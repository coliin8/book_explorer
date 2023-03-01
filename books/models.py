from django.db import models


class BookFile(models.Model):
    file_name = models.CharField(max_length=100)
    s3_url = models.URLField(max_length=200)
    date_uploaded = models.DateTimeField("date uploaded")
    md5_checksum = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.file_name} - {self.md5_checksum}"
