from typing import List, Optional
from pydantic import BaseModel, Field

class Facets(BaseModel):
    function: Optional[str] = None
    topology: Optional[str] = None
    commit: Optional[str] = None
    gate: Optional[List[str]] = None
    substrate: Optional[List[str]] = None
    temporal: Optional[str] = None
    invariants: Optional[List[str]] = None

class Symbol(BaseModel):
    class Config:
        extra = "allow"
    id: str
    description: Optional[str] = None
    name: Optional[str] = None
    macro: Optional[str]  = None
    gate: Optional[List[str]] = None
    facets: Optional[Facets] = None
    failure_mode: Optional[str] = None
    linked_patterns: Optional[List[str]] = None
    symbolic_role: Optional[str] = None
    triad: Optional[str] = None
    invocations: Optional[List[str]] = None
    symbol_domain: Optional[str] = None
    symbol_tag: Optional[str] = None
    version: Optional[int] = None
    origin: Optional[str] = None
    scope: Optional[List[str]] = None


class AgentPersona(BaseModel):
    class Config:
        extra = "allow"

    id: str
    name: Optional[str] = None


class KitDefinition(BaseModel):
    class Config:
        extra = "allow"

    kit: str
    triad: List[str] = Field(default_factory=list)
    anchor: Optional[str] = None
    exec: List[str] = Field(default_factory=list)
