from uuid import UUID
from fastapi import APIRouter,Depends,Query,HTTPException
from app.services.decision_approvals import ApprovalService
from app.schemas.decision_approvals import ReviewRequest,ReviewResponse,Audit
router=APIRouter(prefix='/decisions',tags=['local-demo-human-review-only'])
def get_approval_service():return ApprovalService()
def handler(action):
    def review(proposal_id:str,body:ReviewRequest,store_id:int=Query(gt=0),service=Depends(get_approval_service)):
        try:parsed=UUID(proposal_id)
        except ValueError as e:raise HTTPException(404,'proposal_not_found') from e
        try:return service.review(parsed,store_id,action,body.comment)
        except LookupError as e:raise HTTPException(404,'proposal_not_found') from e
        except ValueError as e:
            if str(e) in ('rejection_reason_required','comment_too_long'):raise HTTPException(422,str(e)) from e
            raise HTTPException(404,'proposal_not_found') from e
        except RuntimeError as e:raise HTTPException(409,'invalid_or_already_reviewed_state') from e
    return review
for action in ('submit','approve','reject'):router.add_api_route('/{proposal_id}/'+action,handler(action),methods=['POST'],response_model=ReviewResponse)
@router.get('/{proposal_id}/audit',response_model=list[Audit])
def audit(proposal_id:str,store_id:int=Query(gt=0),service=Depends(get_approval_service)):
    try:return service.audit(UUID(proposal_id),store_id)
    except (ValueError,LookupError) as e:raise HTTPException(404,'proposal_not_found') from e
