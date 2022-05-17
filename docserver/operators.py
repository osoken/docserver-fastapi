from sqlalchemy.orm import Session

from . import models, schema


def create_user(db: Session, query: schema.UserCreateQuery) -> schema.UserRetrieveResponse:
    user = models.User(username=query.username, hashed_password=query.password.get_hashed_value(), email=query.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return schema.UserRetrieveResponse.from_orm(user)
