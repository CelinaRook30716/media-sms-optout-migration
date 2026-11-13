from src.media_sms_service import CreatorDelivery, decide_delivery


def test_opt_out_wins_before_suppression_or_approval():
    delivery = CreatorDelivery("+15550100", "asset-1", approved=True)

    result = decide_delivery(delivery, suppressed=set(), opted_out={"+15550100"})

    assert result.send is False
    assert result.reason == "creator opted out"


def test_eligible_approved_creator_can_receive_media():
    result = decide_delivery(CreatorDelivery("+15550100", "asset-1", True), set(), set())

    assert result == type(result)(True, "approved and eligible")
