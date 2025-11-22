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




class CveOption(models.Model):
    eventName = models.CharField(max_length=200, unique=True)
    # store counts here (keeps read queries fast)
    eventCount = models.BigIntegerField(default=0, help_text="Count of cve_changes rows for this eventName", db_index=True)

    class Meta:
        db_table = "CVE_OPTIONS"
        verbose_name = "CVE Option"
        verbose_name_plural = "CVE Options"

    def __str__(self):
        # return the human-readable name field
        return self.eventName




class CveYearCount(models.Model):
    event_year = models.IntegerField(db_index=True)
    count = models.BigIntegerField(default=0)

    class Meta:
        db_table = "cve_year_counts"
        verbose_name = "CVE Year Count"
        verbose_name_plural = "CVE Year Counts"
        ordering = ["event_year"]

    def __str__(self):
        return f"{self.event_year}: {self.count}"
    



class CveAnalysisStatus(models.Model):
    status_label = models.CharField(max_length=100, unique=True, db_index=True)
    count = models.BigIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cve_analysis_status"
        verbose_name = "CVE Analysis Status"
        verbose_name_plural = "CVE Analysis Statuses"
        ordering = ["-count"]

    def __str__(self):
        return f"{self.status_label}: {self.count}"