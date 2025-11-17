from django.db import models

class CveChange(models.Model):
    cveId = models.CharField(max_length=50)
    eventName = models.CharField(max_length=100)
    cveChangeId = models.CharField(max_length=100, unique=True)
    sourceIdentifier = models.CharField(max_length=255)
    created = models.DateTimeField()
    details = models.JSONField(default=list, blank=True)


    class Meta:
        db_table = 'cve_changes'

    def __str__(self):
        return f"{self.cveId} - {self.eventName}"
