from jkit._base import ResourceObject
from jkit._network import send_request
from jkit.credentials import JianshuCredential


class Membership(ResourceObject):
    def __init__(self, *, credential: JianshuCredential) -> None:
        self._credential = credential

    @property
    async def referral_url(self) -> str:
        data = await send_request(
            datasource="JIANSHU",
            method="GET",
            path="/asimov/member_distributions",
            credential=self._credential,
            response_type="JSON",
        )

        referral_slug = data["agent_ref"]

        return f"https://www.jianshu.com/mobile/club?ref={referral_slug}"
