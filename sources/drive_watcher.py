python
from fastn import FastnClient

fastn = FastnClient()

DRIVE_FOLDER_ID = "your_drive_folder_id"  # from the folder's URL

def fetch_recent_files():
    """
    ⚠️ VERIFY: connector slug may be 'google_drive', 'googledrive', or 'drive' —
    check with: fastn connector ls   (search the printed list)
    then:       fastn connector ls <the real name>
    """
    files = fastn.google_drive.list_files(
        folder_id=DRIVE_FOLDER_ID,
        modified_after="1d",  # confirm exact parameter name/format from the connector schema
    )
    results = []
    for f in files.get("files", []):
        content = fastn.google_drive.get_file_text(file_id=f["id"])  # ⚠️ VERIFY method name
        results.append({
            "id": f["id"],
            "name": f.get("name", ""),
            "content": content,
        })
    return results