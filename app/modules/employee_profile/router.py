"""
Employee Profile Router
Provides endpoints for managing the extended employee profile including:
  - Personal info, contact, address
  - Employment details
  - Emergency contacts
  - Documents
  - Education & Experience records
  - Profile photo upload
  - Org chart (direct reports)
"""
import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_tenant_db_from_token, get_current_user
from app.modules.core_hr.models import User, Department
from app.modules.employee_profile import models, schemas

router = APIRouter()

UPLOAD_DIR = "/app/uploads/profile_photos"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: auto-generate employee_id like EMP-001
# ─────────────────────────────────────────────────────────────────────────────
async def generate_employee_id(db: AsyncSession) -> str:
    result = await db.execute(select(models.EmployeeProfile))
    count = len(result.scalars().all())
    return f"EMP-{(count + 1):04d}"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: load profile with all relationships
# ─────────────────────────────────────────────────────────────────────────────
async def get_profile_or_404(profile_id: int, db: AsyncSession) -> models.EmployeeProfile:
    result = await db.execute(
        select(models.EmployeeProfile)
        .options(
            selectinload(models.EmployeeProfile.emergency_contacts),
            selectinload(models.EmployeeProfile.documents),
            selectinload(models.EmployeeProfile.education_records),
            selectinload(models.EmployeeProfile.experience_records),
        )
        .where(models.EmployeeProfile.id == profile_id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    return profile


# ═════════════════════════════════════════════
# EMPLOYEE PROFILE — CRUD
# ═════════════════════════════════════════════

@router.post(
    "/",
    response_model=schemas.EmployeeProfileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create employee profile"
)
async def create_employee_profile(
    data: schemas.EmployeeProfileCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    """Create an extended profile for a user. Only superusers can create profiles for others."""
    if not current_user.is_superuser and data.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create profile for another user")

    # Check target user exists
    user_result = await db.execute(select(User).where(User.id == data.user_id))
    if not user_result.scalars().first():
        raise HTTPException(status_code=404, detail="Target user not found")

    # Check profile doesn't already exist
    existing = await db.execute(
        select(models.EmployeeProfile).where(models.EmployeeProfile.user_id == data.user_id)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Profile already exists for this user")

    # Auto-generate employee_id if not provided
    emp_id = data.employee_id or await generate_employee_id(db)

    profile = models.EmployeeProfile(
        **data.model_dump(exclude={"employee_id"}),
        employee_id=emp_id
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return await get_profile_or_404(profile.id, db)


@router.get(
    "/me",
    response_model=schemas.EmployeeProfileOut,
    summary="Get my own employee profile"
)
async def get_my_profile(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    """Returns the profile for the currently authenticated user."""
    result = await db.execute(
        select(models.EmployeeProfile)
        .options(
            selectinload(models.EmployeeProfile.emergency_contacts),
            selectinload(models.EmployeeProfile.documents),
            selectinload(models.EmployeeProfile.education_records),
            selectinload(models.EmployeeProfile.experience_records),
        )
        .where(models.EmployeeProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please create your profile first.")
    return profile


@router.get(
    "/{profile_id}",
    response_model=schemas.EmployeeProfileOut,
    summary="Get employee profile by ID"
)
async def get_employee_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    return await get_profile_or_404(profile_id, db)


@router.get(
    "/by-user/{user_id}",
    response_model=schemas.EmployeeProfileOut,
    summary="Get employee profile by User ID"
)
async def get_profile_by_user(
    user_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.EmployeeProfile)
        .options(
            selectinload(models.EmployeeProfile.emergency_contacts),
            selectinload(models.EmployeeProfile.documents),
            selectinload(models.EmployeeProfile.education_records),
            selectinload(models.EmployeeProfile.experience_records),
        )
        .where(models.EmployeeProfile.user_id == user_id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found for this user")
    return profile


@router.patch(
    "/{profile_id}",
    response_model=schemas.EmployeeProfileOut,
    summary="Update employee profile"
)
async def update_employee_profile(
    profile_id: int,
    data: schemas.EmployeeProfileUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    """Update allowed fields of the profile. Employees can update their own; admins can update any."""
    profile = await get_profile_or_404(profile_id, db)

    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this profile")

    update_data = data.model_dump(exclude_unset=True)

    # Handle user-level fields
    user_fields = ['first_name', 'last_name', 'job_title', 'department_id']
    user_updates = {f: update_data.pop(f) for f in user_fields if f in update_data}

    for field, value in update_data.items():
        setattr(profile, field, value)

    if user_updates:
        user_result = await db.execute(select(User).where(User.id == profile.user_id))
        user_obj = user_result.scalars().first()
        if user_obj:
            for field, value in user_updates.items():
                setattr(user_obj, field, value)

    await db.commit()
    await db.refresh(profile)
    return await get_profile_or_404(profile_id, db)


@router.patch(
    "/me/update",
    response_model=schemas.EmployeeProfileOut,
    summary="Update my own profile"
)
async def update_my_profile(
    data: schemas.EmployeeProfileUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.EmployeeProfile).where(models.EmployeeProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Create your profile first.")

    update_data = data.model_dump(exclude_unset=True)

    # Handle user-level fields
    user_fields = ['first_name', 'last_name', 'job_title', 'department_id']
    user_updates = {f: update_data.pop(f) for f in user_fields if f in update_data}

    for field, value in update_data.items():
        setattr(profile, field, value)

    if user_updates:
        user_result = await db.execute(select(User).where(User.id == profile.user_id))
        user_obj = user_result.scalars().first()
        if user_obj:
            for field, value in user_updates.items():
                setattr(user_obj, field, value)

    await db.commit()
    await db.refresh(profile)
    return await get_profile_or_404(profile.id, db)


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete employee profile (admin only)"
)
async def delete_employee_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only admins can delete profiles")
    profile = await get_profile_or_404(profile_id, db)
    await db.delete(profile)
    await db.commit()


# ═════════════════════════════════════════════
# PHOTO UPLOAD
# ═════════════════════════════════════════════

@router.post(
    "/{profile_id}/upload-photo",
    summary="Upload profile photo"
)
async def upload_profile_photo(
    profile_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)

    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are allowed")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Save relative URL
    photo_url = f"/uploads/profile_photos/{filename}"
    profile.profile_photo_url = photo_url
    await db.commit()

    return {"message": "Photo uploaded successfully", "profile_photo_url": photo_url}


# ═════════════════════════════════════════════
# EMERGENCY CONTACTS
# ═════════════════════════════════════════════

@router.post(
    "/{profile_id}/emergency-contacts",
    response_model=schemas.EmergencyContactOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add emergency contact"
)
async def add_emergency_contact(
    profile_id: int,
    data: schemas.EmergencyContactCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    contact = models.EmergencyContact(**data.model_dump(), profile_id=profile_id)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.get(
    "/{profile_id}/emergency-contacts",
    response_model=List[schemas.EmergencyContactOut],
    summary="List emergency contacts"
)
async def list_emergency_contacts(
    profile_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.EmergencyContact).where(models.EmergencyContact.profile_id == profile_id)
    )
    return result.scalars().all()


@router.patch(
    "/{profile_id}/emergency-contacts/{contact_id}",
    response_model=schemas.EmergencyContactOut,
    summary="Update emergency contact"
)
async def update_emergency_contact(
    profile_id: int,
    contact_id: int,
    data: schemas.EmergencyContactUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(models.EmergencyContact).where(
            models.EmergencyContact.id == contact_id,
            models.EmergencyContact.profile_id == profile_id
        )
    )
    contact = result.scalars().first()
    if not contact:
        raise HTTPException(status_code=404, detail="Emergency contact not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)

    await db.commit()
    await db.refresh(contact)
    return contact


@router.delete(
    "/{profile_id}/emergency-contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete emergency contact"
)
async def delete_emergency_contact(
    profile_id: int,
    contact_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(models.EmergencyContact).where(
            models.EmergencyContact.id == contact_id,
            models.EmergencyContact.profile_id == profile_id
        )
    )
    contact = result.scalars().first()
    if not contact:
        raise HTTPException(status_code=404, detail="Emergency contact not found")
    await db.delete(contact)
    await db.commit()


# ═════════════════════════════════════════════
# DOCUMENTS
# ═════════════════════════════════════════════

@router.post(
    "/{profile_id}/documents",
    response_model=schemas.EmployeeDocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add employee document"
)
async def add_document(
    profile_id: int,
    data: schemas.EmployeeDocumentCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    doc = models.EmployeeDocument(**data.model_dump(), profile_id=profile_id)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get(
    "/{profile_id}/documents",
    response_model=List[schemas.EmployeeDocumentOut],
    summary="List employee documents"
)
async def list_documents(
    profile_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.EmployeeDocument).where(models.EmployeeDocument.profile_id == profile_id)
    )
    return result.scalars().all()


@router.patch(
    "/{profile_id}/documents/{doc_id}",
    response_model=schemas.EmployeeDocumentOut,
    summary="Update employee document"
)
async def update_document(
    profile_id: int,
    doc_id: int,
    data: schemas.EmployeeDocumentUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(models.EmployeeDocument).where(
            models.EmployeeDocument.id == doc_id,
            models.EmployeeDocument.profile_id == profile_id
        )
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(doc, field, value)

    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete(
    "/{profile_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete employee document"
)
async def delete_document(
    profile_id: int,
    doc_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(models.EmployeeDocument).where(
            models.EmployeeDocument.id == doc_id,
            models.EmployeeDocument.profile_id == profile_id
        )
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.commit()


# ═════════════════════════════════════════════
# EDUCATION RECORDS
# ═════════════════════════════════════════════

@router.post(
    "/{profile_id}/education",
    response_model=schemas.EducationRecordOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add education record"
)
async def add_education(
    profile_id: int,
    data: schemas.EducationRecordCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    record = models.EducationRecord(**data.model_dump(), profile_id=profile_id)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get(
    "/{profile_id}/education",
    response_model=List[schemas.EducationRecordOut],
    summary="List education records"
)
async def list_education(
    profile_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.EducationRecord).where(models.EducationRecord.profile_id == profile_id)
    )
    return result.scalars().all()


@router.patch(
    "/{profile_id}/education/{edu_id}",
    response_model=schemas.EducationRecordOut,
    summary="Update education record"
)
async def update_education(
    profile_id: int,
    edu_id: int,
    data: schemas.EducationRecordUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(models.EducationRecord).where(
            models.EducationRecord.id == edu_id,
            models.EducationRecord.profile_id == profile_id
        )
    )
    record = result.scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Education record not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)

    await db.commit()
    await db.refresh(record)
    return record


@router.delete(
    "/{profile_id}/education/{edu_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete education record"
)
async def delete_education(
    profile_id: int,
    edu_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(models.EducationRecord).where(
            models.EducationRecord.id == edu_id,
            models.EducationRecord.profile_id == profile_id
        )
    )
    record = result.scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Education record not found")
    await db.delete(record)
    await db.commit()


# ═════════════════════════════════════════════
# EXPERIENCE RECORDS
# ═════════════════════════════════════════════

@router.post(
    "/{profile_id}/experience",
    response_model=schemas.ExperienceRecordOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add experience record"
)
async def add_experience(
    profile_id: int,
    data: schemas.ExperienceRecordCreate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    record = models.ExperienceRecord(**data.model_dump(), profile_id=profile_id)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get(
    "/{profile_id}/experience",
    response_model=List[schemas.ExperienceRecordOut],
    summary="List experience records"
)
async def list_experience(
    profile_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.ExperienceRecord).where(models.ExperienceRecord.profile_id == profile_id)
    )
    return result.scalars().all()


@router.patch(
    "/{profile_id}/experience/{exp_id}",
    response_model=schemas.ExperienceRecordOut,
    summary="Update experience record"
)
async def update_experience(
    profile_id: int,
    exp_id: int,
    data: schemas.ExperienceRecordUpdate,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(models.ExperienceRecord).where(
            models.ExperienceRecord.id == exp_id,
            models.ExperienceRecord.profile_id == profile_id
        )
    )
    record = result.scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Experience record not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)

    await db.commit()
    await db.refresh(record)
    return record


@router.delete(
    "/{profile_id}/experience/{exp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete experience record"
)
async def delete_experience(
    profile_id: int,
    exp_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    profile = await get_profile_or_404(profile_id, db)
    if not current_user.is_superuser and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(models.ExperienceRecord).where(
            models.ExperienceRecord.id == exp_id,
            models.ExperienceRecord.profile_id == profile_id
        )
    )
    record = result.scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Experience record not found")
    await db.delete(record)
    await db.commit()


# ═════════════════════════════════════════════
# EMPLOYEE DIRECTORY & ORG CHART
# ═════════════════════════════════════════════

@router.get(
    "/directory/all",
    response_model=List[schemas.EmployeeSummary],
    summary="Employee directory — all employees with basic info"
)
async def employee_directory(
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    """Returns a summary list of all employees — useful for directory/org chart pages."""
    from sqlalchemy.orm import selectinload

    query = (
        select(User)
        .options(
            selectinload(User.department),
            selectinload(User.profile)
        )
        .where(User.is_active == True)
    )

    if department_id:
        query = query.where(User.department_id == department_id)

    if search:
        from sqlalchemy import or_
        search_term = f"%{search}%"
        query = query.where(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.email.ilike(search_term),
                User.job_title.ilike(search_term)
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    # Build summary list
    summaries = []
    for u in users:
        profile = u.profile if hasattr(u, "profile") else None
        summaries.append(schemas.EmployeeSummary(
            id=u.id,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            job_title=u.job_title,
            profile_photo_url=profile.profile_photo_url if profile else None,
            department=u.department
        ))

    return summaries


@router.get(
    "/org-chart/{manager_id}",
    response_model=List[schemas.EmployeeSummary],
    summary="Get direct reports for a manager"
)
async def get_direct_reports(
    manager_id: int,
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    """Returns list of employees who report directly to the given manager."""
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(models.EmployeeProfile)
        .options(
            selectinload(models.EmployeeProfile.user).selectinload(User.department)
        )
        .where(models.EmployeeProfile.manager_id == manager_id)
    )
    profiles = result.scalars().all()

    summaries = []
    for p in profiles:
        u = p.user
        summaries.append(schemas.EmployeeSummary(
            id=u.id,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            job_title=u.job_title,
            profile_photo_url=p.profile_photo_url,
            department=u.department
        ))

    return summaries


@router.get(
    "/org-tree",
    response_model=List[schemas.OrgNode],
    summary="Full org tree — all employees with their manager_id in one call"
)
async def get_org_tree(
    db: AsyncSession = Depends(get_tenant_db_from_token),
    current_user: User = Depends(get_current_user)
):
    """
    Returns ALL employees as a flat list with their manager_id.
    The frontend uses this single call to build the full hierarchical org chart.
    Employees with manager_id=None are the root nodes (CEO / Founders).
    """
    # Fetch all users with their department
    users_result = await db.execute(
        select(User)
        .options(selectinload(User.department))
        .where(User.is_active == True)
    )
    users = {u.id: u for u in users_result.scalars().all()}

    # Fetch all profiles (to get manager_id and photo)
    profiles_result = await db.execute(
        select(models.EmployeeProfile)
    )
    profiles = {p.user_id: p for p in profiles_result.scalars().all()}

    nodes = []
    for user_id, u in users.items():
        profile = profiles.get(user_id)
        nodes.append(schemas.OrgNode(
            user_id=u.id,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            job_title=u.job_title,
            profile_photo_url=profile.profile_photo_url if profile else None,
            department=u.department,
            manager_id=profile.manager_id if profile else None,
            employment_status=profile.employment_status.value if profile and profile.employment_status else None,
            is_active=u.is_active,
        ))

    return nodes
