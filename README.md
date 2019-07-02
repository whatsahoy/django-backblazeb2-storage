BACKBLAZE B2 Storage for Django
================================

BackBlaze B2 Storage for django.

###installation
via PIP:

    pip install git://github.com/whatsahoy/django-backblazeb2-storage.git

Manual:

clone this repo locally using `git clone git@github.com:whatsahoy/django-backblazeb2-storage.git`
and run `python setup.py install`

###Usage

Set this in ypour settings (usualy settings.py)

    BACKBLAZEB2_ACCOUNT_ID = 'your-account-id'
    BACKBLAZEB2_APP_KEY = 'your-app-key'
    BACKBLAZEB2_BUCKET_NAME = 'bucketname'
    BACKBLAZEB2_BUCKET_ID = 'bucket-id' # optinal but will speed up initialization
    BACKBLAZEB2_BUCKET_PRIVATE = 'is-bucket-private'

To make it your default django storage : 


    DEFAULT_FILE_STORAGE = 'b2_storage.B2Storage'


if you are making alot of api calls I recommend you to initialize b2_storage.B2Storage in your settings to a variable
and then write function in settings to return this variable. Then for file storage pass this function, so the authorization call will be called only once at the start of python worker.
eg.
	
    B2_FILE_STORAGE = B2Storage(
        account_id=BACKBLAZEB2_ACCOUNT_ID,
        app_key=BACKBLAZEB2_APP_KEY,
        bucket_name=BACKBLAZEB2_BUCKET_NAME_PRIV,
    )
    DEFAULT_FILE_STORAGE = 'ahoy.api.private_b2storage'

and
	
	def private_b2storage():
	    return settings.B2_FILE_STORAGE

Storage Implimentation : 

- save

    Save the file (overwrite if it already exists)

- open

    Open a file using the filename (the latest version of the file).

- delete

    Deletes the file (all versions of the file)
    

some notes :

Everytime you overwrite a file in backblaze b2 it will create a new file version.
When you download the file the latest version will be downloaded. 
this is the same behavior as s3 but it is enabled be default.
