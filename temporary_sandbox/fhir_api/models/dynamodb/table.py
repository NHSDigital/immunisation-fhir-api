"""Models for interacting with tables"""

from pydantic import (
    BaseModel,
    Field,
)


class KeySchema(BaseModel):
    AttributeName: str = Field(
        description="Attribute Name for Key Schema", example="year"
    )
    KeyType: str = Field(description="Key Type for Key Schema", example="HASH")


class AttributeDefinitions(BaseModel):
    AttributeName: str = Field(
        description="Attribute Name for Attribute Definition", example="year"
    )
    AttributeType: str = Field(
        description="Attribute Type for Attribute Definition", example="N"
    )


class ProvisionedThroughput(BaseModel):
    ReadCapacityUnits: int = Field(description="Read Capacity Units", example=10)
    WriteCapacityUnits: int = Field(description="Write Capacity Units", example=10)


class CreateTable(BaseModel):
    table_name: str
    key_schema: list[KeySchema]
    attribute_definition: list[AttributeDefinitions]
    provisioned_throughput: ProvisionedThroughput
