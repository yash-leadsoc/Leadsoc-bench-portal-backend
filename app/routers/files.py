"""Generic secure file upload/download used across Materials, Interview Prep,
Question Bank and Employee documents. One storage folder, one download route."""
import os, uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
import cloudinary
import cloudinary.uploader

from .. import config

from ..deps import current_user

router = APIRouter(tags=["files"])
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
           ".csv", ".txt", ".png", ".jpg", ".jpeg", ".zip"}


def _type(ext: str) -> str:
    ext = ext.lower()
    if ext == ".pdf": return "pdf"
    if ext in (".doc", ".docx"): return "doc"
    if ext in (".ppt", ".pptx"): return "ppt"
    if ext in (".xls", ".xlsx", ".csv"): return "excel"
    if ext in (".png", ".jpg", ".jpeg"): return "image"
    return "other"


# @router.post("/files/upload")
# async def upload_file(file: UploadFile = File(...), user=Depends(current_user)):
#     ext = os.path.splitext(file.filename)[1].lower()
#     if ext not in ALLOWED:
#         raise HTTPException(400, f"File type {ext} not allowed")
#     data = await file.read()
#     try:
#         # resource_type="raw" delivers docs/ppt/xlsx/pdf back byte-for-byte,
#         # which is what we want for download. (Use "auto" if you want image/
#         # video previews instead — note some accounts block raw PDF delivery.)
#         res = cloudinary.uploader.upload(
#             data, resource_type="raw", folder="leadsoc/materials",
#             use_filename=True, unique_filename=True,
#             filename_override=file.filename)
#     except Exception as e:
#         raise HTTPException(502, f"Cloud upload failed: {e}")
#     url = res["secure_url"]
#     download_url = url.replace("/upload/", "/upload/fl_attachment/")  # forces download
#     return {"url": url, "downloadUrl": download_url,
#             "fileName": file.filename, "fileType": _type(ext)}

@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    user=Depends(current_user)):
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in ALLOWED:
        raise HTTPException(400, f"File type {ext} not allowed")

    data = await file.read()

    try:
        res = cloudinary.uploader.upload(
            data,
            resource_type="raw",
            folder="leadsoc/materials",
            use_filename=True,
            unique_filename=True,
            filename_override=file.filename,
        )

    except Exception as e:
        print("Cloudinary upload error:", repr(e))
        raise HTTPException(
            status_code=502,
            detail=f"Cloud upload failed: {str(e)}"
        )

    return {
        "url": res["secure_url"],
        "downloadUrl": res["secure_url"],
        "publicId": res["public_id"],
        "fileName": file.filename,
        "fileType": _type(ext),
    }


@router.get("/files/{fname}")
def download_file(fname: str):
    path = os.path.join(UPLOAD_DIR, fname)
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=fname, headers={
        "Content-Disposition": f'attachment; filename="{fname}"',
        "Access-Control-Allow-Origin": "*"})
