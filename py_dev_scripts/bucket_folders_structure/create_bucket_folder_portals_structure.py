import oci

# Load config and initialize client 
config = oci.config.from_file("~/.oci/config")
object_storage = oci.object_storage.ObjectStorageClient(config)
namespace = object_storage.get_namespace().data
bucket_name = "news-raw-data"

# Portal folders to create
portals = [
    "nyt/",
    "bbc/",
    "cnn/",
    "guardian/",
    "reuters/",
    "wapo/",
    "aljazeera/",
    "fox/",
    "cnbc/",
    "bloomberg/",
    "ft/",
    "forbes/",
    "politico/",
    "npr/",
    "abcnews/",
    "nbcnews/",
    "hindu/",
    "toi/",
    "scmp/",
    "lemonde/"
]

# Create portal folders
def create_folder(path):
    try:
        object_storage.head_object(namespace, bucket_name, path)
        print(f"Folder exists: {path}")
    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            object_storage.put_object(namespace, bucket_name, path, put_object_body="")
            print(f"Created folder: {path}")
        else:
            raise

# Create each portal folder
for portal in portals:
    create_folder(portal)

print("Portal folders created successfully.")