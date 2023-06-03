from django.views.decorators.cache import cache_control
from django.http import HttpResponse
from .tasks import report_generation
from celery.result import AsyncResult
from django.shortcuts import render
from django.contrib import messages
from .models import TaskCache
import os


@cache_control(must_revalidate=True, max_age=0, no_cache=True, no_store=True)
def report_initiation(request):
    x = report_generation.delay()
    context = {'task_id': str(x.task_id)}
    temp = TaskCache(task_id=x.task_id)
    temp.save()
    return render(request, 'report-initiated.html',context)

@cache_control(must_revalidate=True, max_age=0, no_cache=True, no_store=True)
def report_collection(request):
    if request.method == 'GET':
        return render(request, 'get-report.html')
    
    if request.method == 'POST':
        task_id = request.POST.get('report_id')
        task = AsyncResult(task_id)
        if task.state == 'SUCCESS':
            file_location = os.getcwd() + '/Apps/TaskForMe/GeneratedReports/'+task_id+'.csv'
            if os.path.exists(file_location):
                """
                return FileResponse(open(file_location, 'rb'), as_attachment=True)
                """
                response = HttpResponse(open(file_location, 'rb'), content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="report.csv"'
                response['Content-Length'] = os.path.getsize(file_location)
                messages.success(request, f"Completed")
                return response
            else:
                messages.error(request, f"File with Report-ID Not Found, Retry Report Initiation")
                try:    
                    instance = TaskCache.objects.get(task_id=task_id)
                    instance.delete()
                except:
                    messages.error(request, f"Invalid Report-ID")
                        
        elif task.state == 'RECEIVED' or task.state == 'STARTED' or task.state == 'RETRY':
            messages.warning(request, f"Running")    
            return render(request, 'get-report.html')
        
        else:
            exists = TaskCache.objects.filter(task_id=task_id).exists()
            if exists:
                messages.error(request, f"Running")
            else:
                messages.error(request, f"Invalid Report-ID")
        
        return render(request, 'get-report.html')