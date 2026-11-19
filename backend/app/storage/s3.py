"""Storage S3 compatible (Supabase Storage S3 API u otro). Bucket privado; URLs prefirmadas de GET.

Supabase: S3_ENDPOINT_URL=https://<ref>.supabase.co/storage/v1/s3, S3_REGION=us-east-1 (path-style).
"""

from app.storage.base import validate_key


class S3Storage:
    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region: str = "auto",
        client=None,
    ):
        self.bucket = bucket
        if client is None:
            import boto3
            from botocore.config import Config

            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url or None,
                aws_access_key_id=access_key_id or None,
                aws_secret_access_key=secret_access_key or None,
                region_name=region or None,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                              retries={"max_attempts": 3}),
            )
        self.client = client

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        validate_key(key)
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return key

    def get(self, key: str) -> bytes:
        validate_key(key)
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=key)
        except self.client.exceptions.NoSuchKey as exc:
            raise FileNotFoundError(key) from exc
        return obj["Body"].read()

    def url(self, key: str, expires: int = 600) -> str:
        validate_key(key)
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires
        )

    def delete(self, key: str) -> None:
        validate_key(key)
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        validate_key(key)
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
