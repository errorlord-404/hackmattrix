from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.gov_scheme import GovScheme


class GovSchemeMutator(ABC):
    @abstractmethod 
    async def check_scheme_eligibility(
        self,
        farmer_state: str,
        eligibility_criteria: Optional[List[str]] = None,
    ) -> List[GovScheme]:
        raise NotImplementedError


class MongoGovSchemeMutator(GovSchemeMutator):
    async def check_scheme_eligibility(
        self,
        farmer_state: str,
        eligibility_criteria: Optional[List[str]] = None,
    ) -> List[GovScheme]:
        # PRD section 22 currently requires state-based eligibility only.
        # Additional criteria are accepted for interface stability but not applied yet.
        _ = eligibility_criteria
        return await GovScheme.find(
            (GovScheme.applicable_states == []) | (GovScheme.applicable_states.in_([farmer_state]))
        ).to_list()


def get_gov_scheme_mutator() -> GovSchemeMutator:
    return MongoGovSchemeMutator()
