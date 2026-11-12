# Паттерн Adapter: порт ObjectStorage + реализации MinIO и локальная
import os

class ObjectStorage:
    def put_bytes(self, key, data):
        raise NotImplementedError
    def get_bytes(self, key):
        raise NotImplementedError

class MinioStore(ObjectStorage):
    def __init__(self, endpoint, access, secret, bucket):
        from minio import Minio
        self.client = Minio(endpoint, access_key=access, secret_key=secret, secure=False)
        self.bucket = bucket
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def put_bytes(self, key, data):
        import io
        self.client.put_object(self.bucket, key, io.BytesIO(data), len(data))

    def get_bytes(self, key):
        return self.client.get_object(self.bucket, key).read()

class LocalStore(ObjectStorage):
    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _path(self, key):
        return os.path.join(self.root, key)

    def put_bytes(self, key, data):
        p = self._path(key)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)

    def get_bytes(self, key):
        with open(self._path(key), "rb") as f:
            return f.read()

def make_storage():
    if os.getenv("USE_LOCAL_STORAGE") == "1":
        return LocalStore(os.getenv("LOCAL_STORAGE_DIR", "./data/storage"))
    return MinioStore(
        os.getenv("MINIO_ENDPOINT", "minio:9000"),
        os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        os.getenv("MINIO_BUCKET", "media"),
    )
