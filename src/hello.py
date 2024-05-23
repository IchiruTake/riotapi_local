import pydantic

class Tags(pydantic.BaseModel):
    commit : str = pydantic.Field(alias="mlflow.source.git.commit")

data = {
  "mlflow.source.git.commit": "fbe812fe",
  "other.key": "other.value"
}

t = Tags(**data)
print(t)