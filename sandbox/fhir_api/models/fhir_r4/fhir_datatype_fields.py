''' Generic Fields for FHIR Revision 4 '''

import datetime

from typing import Union
from functools import partial
from pydantic import (
    Field,
    AnyUrl,
    conint,
    PositiveInt,
)


class FhirR4Fields:
    """ Generic Fields, descriptions and examples"""
    _pk: str = Field(
        description="Partition Key for DynamoDB",
        example="P#1000"
    )

    _sk: str = Field(
        description="Sorting Key for DynamoDB",
        example="P#1000",
    )

    boolean: bool = Field(
        description="Boolean Field",
        example="True",
    )

    string: str = Field(
        description="A sequence of Unicode characters",
        example="text",
        regex=r"[ \r\n\t\S]+",
    )

    integer: int = Field(
        description="A signed integer in the range −2,147,483,648..2,147,483,647 (32-bit; for larger values, use decimal)",
        example=100,
    )

    decimal: float = Field(
        description="Rational numbers that have a decimal representation. See below about the precision of the number",
        example=100.01,
    )

    uri: str = Field(
        description="A Uniform Resource Identifier Reference",
        example="urn:uuid:53fefa32-fcbb-4ff8-8a92-55ee120877b7",
        regex=r"\S*"
    )

    url: AnyUrl = Field(
        description="A Uniform Resource Locator",
        example="http://terminology.hl7.org/CodeSystem/v2-0203",
    )

    canonical: str = Field(
        description="A URI that refers to a resource by its canonical URL",
        example="http://fhir.acme.com/Questionnaire/example|1.0#vs1",
    )

    # Pydantic currently has no Base64 validation, so using [str] instead
    base64Binary: str = Field(
        description="A stream of bytes, base64 encoded",
        example="eyJmbGF2b3IiOiAiZnJlbmNoIHZhbmlsbGEiLCAic2l6ZSI6ICIyNCBveiJ9",
        regex=r"(\s*([0-9a-zA-Z\+\=]){4}\s*)+"
    )

    instant: datetime.datetime = Field(
        description="An instant in time in the format YYYY-MM-DDThh:mm:ss.sss+zz:zz",
        example="2015-02-07T13:28:17.239+02:00",
    )

    date: Union[
        datetime.date,
        partial(datetime.date, day=1),
        partial(datetime.date, month=1, day=1)
    ] = Field(
        description="A date, or partial date (e.g. just year or year + month) as used in human communication",
        example="1905-08-23"
    )

    dateTime: str = Field(
        description="A date, date-time or partial date (e.g. just year or year + month) as used in human communication.",
        example="2015-02-07T13:28:17-05:00",
#        regex=r"([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2][0-9]|3[0-1])(T([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]+)?(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00)))?)?)?"
    )

    time: datetime.time = Field(
        description="A time during the day, in the format hh:mm:ss. There is no date specified.",
        example="01:00:01"
    )

    code: str = Field(
        description="Indicates that the value is taken from a set of controlled strings defined elsewhere",
        example="home",
        regex=r"[^\s]+(\s[^\s]+)*"
    )

    oid: str = Field(
        description="An OID represented as a URI",
        example="urn:oid:1.2.3.4.5",
        regex=r"urn:oid:[0-2](\.(0|[1-9][0-9]*))+"
    )

    id: str = Field(
        description="Any combination of upper- or lower-case ASCII letters",
        example="53fefa32-fcbb-4ff8-8a92-55ee120877b7",
        regex=r"[A-Za-z0-9\-\.]{1,64}",
        max_length=64
    )

    markdown: str = Field(
        description="A FHIR string (see above) that may contain markdown syntax",
        example="A String `with Markdown` in it",
    )

    unsignedInt: conint(ge=0) = Field(
        description="Any non-negative integer in the range 0..2,147,483,647",
        example=123,
    )

    positiveInt: PositiveInt = Field(
        description="Any positive integer in the range 1..2,147,483,647",
        example=123,
    )

    uuid: str = Field(
        description="A UUID (aka GUID) represented as a URI",
        example="urn:uuid:c757873d-ec9a-4326-a141-556f43239520"
    )
