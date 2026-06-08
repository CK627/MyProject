from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.models import SchoolInfo, Department, Facility
from ..schemas.announcement import SchoolInfoResponse, DepartmentResponse, FacilityResponse

router = APIRouter(prefix="/school", tags=["学校信息"])


@router.get("/info", response_model=SchoolInfoResponse, summary="获取学校信息")
async def get_school_info(db: Session = Depends(get_db)):
    """获取学校基本信息"""
    school = db.query(SchoolInfo).first()
    
    if not school:
        return SchoolInfoResponse(
            id=0,
            name="智慧校园",
            description="欢迎使用智慧校园服务平台"
        )
    
    return school


@router.get("/departments", response_model=list[DepartmentResponse], summary="获取院系列表")
async def get_departments(
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取院系列表"""
    query = db.query(Department)
    
    if keyword:
        query = query.filter(Department.name.contains(keyword))
    
    departments = query.all()
    
    return departments


@router.get("/departments/{department_id}", response_model=DepartmentResponse, summary="获取院系详情")
async def get_department(
    department_id: int,
    db: Session = Depends(get_db)
):
    """获取院系详情"""
    department = db.query(Department).filter(Department.id == department_id).first()
    
    if not department:
        return None
    
    return department


@router.get("/facilities", response_model=list[FacilityResponse], summary="获取设施列表")
async def get_facilities(
    type: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取校园设施列表"""
    query = db.query(Facility)
    
    if type:
        query = query.filter(Facility.type == type)
    
    if keyword:
        query = query.filter(
            (Facility.name.contains(keyword)) |
            (Facility.description.contains(keyword))
        )
    
    facilities = query.all()
    
    return facilities


@router.get("/facilities/{facility_id}", response_model=FacilityResponse, summary="获取设施详情")
async def get_facility(
    facility_id: int,
    db: Session = Depends(get_db)
):
    """获取设施详情"""
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    
    if not facility:
        return None
    
    return facility
