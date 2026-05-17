import uuid

from fastapi import APIRouter

from app.core.dependencies import DbDep, OrgContext, RequireAdmin, RequireOwner
from app.schemas.auth import InviteOut, InviteRequest
from app.schemas.common import ApiResponse, MessageResponse
from app.schemas.organization import (
    MemberOut,
    MemberUserOut,
    OrganizationResponse,
    OrgMeResponse,
    UpdateMemberRoleRequest,
    UpdateOrgRequest,
)
from app.services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me")
async def get_org(ctx: OrgContext, db: DbDep) -> ApiResponse[OrgMeResponse]:
    _, org, _ = ctx
    _, members = await organization_service.get_org_with_members(db, org.id)
    return ApiResponse(
        data=OrgMeResponse(
            org=OrganizationResponse.model_validate(org),
            members=[
                MemberOut(
                    id=m.id,
                    user=MemberUserOut(
                        id=m.user.id,
                        email=m.user.email,
                        full_name=m.user.full_name,
                    ),
                    role=m.role,
                    joined_at=m.joined_at,
                )
                for m in members
            ],
        )
    )


@router.put("/me")
async def update_org(
    body: UpdateOrgRequest,
    ctx: RequireOwner,
    db: DbDep,
) -> ApiResponse[OrganizationResponse]:
    _, org, _ = ctx
    updated = await organization_service.update_org(db, org.id, body.name)
    return ApiResponse(data=OrganizationResponse.model_validate(updated))


@router.post("/invite", status_code=201)
async def invite_member(
    body: InviteRequest,
    ctx: RequireAdmin,
    db: DbDep,
) -> ApiResponse[InviteOut]:
    user, org, _ = ctx
    invite = await organization_service.invite_member(
        session=db,
        org_id=org.id,
        invited_by_id=user.id,
        email=body.email,
        role=body.role,
    )
    return ApiResponse(
        data=InviteOut(
            invite_id=invite.id,
            message="Invite sent successfully",
            expires_at=invite.expires_at,
        )
    )


@router.get("/members")
async def list_members(ctx: OrgContext, db: DbDep) -> ApiResponse[list[MemberOut]]:
    _, org, _ = ctx
    _, members = await organization_service.get_org_with_members(db, org.id)
    return ApiResponse(
        data=[
            MemberOut(
                id=m.id,
                user=MemberUserOut(
                    id=m.user.id,
                    email=m.user.email,
                    full_name=m.user.full_name,
                ),
                role=m.role,
                joined_at=m.joined_at,
            )
            for m in members
        ]
    )


@router.delete("/members/{membership_id}")
async def remove_member(
    membership_id: uuid.UUID,
    ctx: RequireAdmin,
    db: DbDep,
) -> ApiResponse[MessageResponse]:
    user, org, membership = ctx
    await organization_service.remove_member(
        session=db,
        org_id=org.id,
        membership_id=membership_id,
        acting_user_id=user.id,
        acting_role=membership.role,
    )
    return ApiResponse(data=MessageResponse(message="Member removed"))


@router.put("/members/{membership_id}/role")
async def update_member_role(
    membership_id: uuid.UUID,
    body: UpdateMemberRoleRequest,
    ctx: RequireAdmin,
    db: DbDep,
) -> ApiResponse[MessageResponse]:
    _, org, membership = ctx
    await organization_service.update_member_role(
        session=db,
        org_id=org.id,
        membership_id=membership_id,
        new_role=body.role,
        acting_role=membership.role,
    )
    return ApiResponse(data=MessageResponse(message="Role updated"))
