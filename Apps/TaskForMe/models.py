from django.db import models

class StoreStatus(models.Model):
    store_id = models.BigIntegerField()
    timestamp_utc = models.CharField(max_length=40)
    status = models.CharField(max_length=10)
    
    def __str__(self):
        return "store_id:"+str(self.store_id)+" "+"status:"+str(self.status)

class BusinessHours(models.Model):
    store_id = models.BigIntegerField()
    day = models.IntegerField()
    start_time_local = models.CharField(max_length=40)
    end_time_local = models.CharField(max_length=40)
    
    def __str__(self):
        return "store_id:"+str(self.store_id)+" "+"business_hours"

class StoreTimezone(models.Model):
    store_id = models.BigIntegerField()
    timezone_str = models.CharField(max_length=30)
    
    def __str__(self):
        return "store_id:"+str(self.store_id)+" "+"store_timezone"

class TaskCache(models.Model):
    task_id = models.CharField(max_length=100)
    
    def __str__(self):
        return "task_id:"+str(self.task_id)