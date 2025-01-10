import oci

# Load config and initialize client 
config = oci.config.from_file("~/.oci/config")
object_storage = oci.object_storage.ObjectStorageClient(config)
namespace = object_storage.get_namespace().data
bucket_name = "news-raw-data"

# Root folder
root_folder = "nyt/"

# RSS folder paths extracted from the feed structure
folders = [
    "World/",
    "World/Africa/",
    "World/Americas/", 
    "World/AsiaPacific/",
    "World/Europe/",
    "World/MiddleEast/",
    "US/",
    "US/Education/",
    "US/Politics/",
    "US/Politics/Upshot/",
    "NYRegion/",
    "Business/",
    "Business/EnergyEnvironment/",
    "Business/SmallBusiness/",
    "Business/Economy/",
    "Business/Dealbook/",
    "Business/MediaandAdvertising/",
    "Business/YourMoney/",
    "Technology/",
    "Technology/PersonalTech/",
    "Sports/",
    "Sports/Baseball/",
    "Sports/CollegeBasketball/",
    "Sports/CollegeFootball/",
    "Sports/Golf/",
    "Sports/Hockey/",
    "Sports/ProBasketball/",
    "Sports/ProFootball/",
    "Sports/Soccer/",
    "Sports/Tennis/",
    "Science/",
    "Science/Climate/",
    "Science/Space/",
    "Health/",
    "Health/Well/",
    "Arts/",
    "Arts/ArtandDesign/",
    "Books/Review/",
    "Arts/Dance/",
    "Arts/Movies/",
    "Arts/Music/",
    "Arts/Television/",
    "Arts/Theater/",
    "Style/FashionandStyle/",
    "Style/DiningandWine/",
    "Style/Weddings/",
    "Style/TMagazine/",
    "Travel/",
    "Jobs/",
    "RealEstate/",
    "Automobiles/",
    "Lens/",
    "Obituaries/",
]

# Create folders
def create_folder(path):
    full_path = root_folder + path
    try:
        object_storage.head_object(namespace, bucket_name, full_path)
        print(f"Folder exists: {full_path}")
    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            object_storage.put_object(namespace, bucket_name, full_path, put_object_body="")
            print(f"Created folder: {full_path}")
        else:
            raise

# Create each folder
create_folder(root_folder)  # Create root nyt/ folder first
for folder in folders:
    create_folder(folder)

print("NYT RSS folder structure created successfully.")