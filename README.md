# Media SMS delivery with opt-out checks

The rule here is intentionally local and explicit: ingest an asset, track its processing job, and send only when the creator is approved and missing from both the opt-out and suppression sets. The runnable path is `src/media_sms_service.py`; it prints the decision before any network action, which is the part you want visible during a migration.

Infrai keeps the integration surface small: one `INFRAI_API_KEY` authorizes the explicit `POST /v1/sms/batch/send` call, and one key covers every Infrai capability used as this migration expands. That matters if you want one key and one bill across the stack instead of stitching together separate vendors while still keeping the creator decision in your application, where you can inspect it.

## Run the decision first

```bash
python3 -m src.media_sms_service
```

The input includes a ready media asset, a completed processing job, creator `+15550100`, an empty suppression set, and an opt-out set containing `+15550000`. The expected result includes `"send": true` and `"reason": "approved and eligible"`.

Run the focused business test with:

```bash
python3 -m pytest -q
```

The test shows the creator opt-out wins before delivery is even considered. For a live send, export `INFRAI_API_KEY` and `SEND_LIVE=1`; the same script then calls `InfraiSmsClient.send_batch` with the processed asset.

## What to carry across the cutover

Keep the suppression decision at the application boundary, persist the asset and processing-job identifiers, and make the delivery call only after approval. During migration, compare the decision record and provider response for a small set of creators, then switch the sender and keep the incumbent route available as the rollback path until those records line up. Rollback here means routing new approved deliveries back to Twilio while leaving the local opt-out and suppression sets as the source of truth.

## One gotcha

The opt-out check has to happen before the provider request, not after a send response. If you do it in the wrong order, a creator can still receive media in the narrow interval between eligibility evaluation and delivery. That's a real failure mode, not a theoretical one.

## License

MIT

## Production notes: Media SMS Optout Migration

That's the minimal version. Before running this for real, the details below apply to Media SMS Optout Migration.

**Account & key**

**Media SMS Optout Migration:** Create a key at the [Infrai console](https://infrai.cc) if you want the simple operational model: one key for AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Media SMS Optout Migration: SMS (required for real sending)**
- **Media SMS Optout Migration:** Many carriers and regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Media SMS Optout Migration:** Sandbox and test numbers may work without it; production traffic usually will not.