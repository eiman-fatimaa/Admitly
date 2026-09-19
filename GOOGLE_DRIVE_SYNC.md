# Google Drive Sync contract

Admitly keeps manual upload as the default submission path. Google Drive discovery is optional and applicant-scoped through Fastn.

## Environment

Set these values in the deployed service:

```env
FASTN_DRIVE_SYNC_WEBHOOK=<optional Fastn applicant Drive scan webhook override>
DRIVE_SYNC_CALLBACK_SECRET=<long random shared secret>
```

Configure the Fastn workflow to send `DRIVE_SYNC_CALLBACK_SECRET` in the `X-Admitly-Drive-Sync-Secret` header when calling Admitly back. Do not place that secret in the callback body or a browser request.

## Start request

When an applicant chooses **Connect & Scan Drive**, Admitly posts to `FASTN_DRIVE_SYNC_WEBHOOK`:

```json
{
  "applicant_id": "42",
  "applicant_email": "applicant@example.edu",
  "requirements": [
    {"item": "Official Transcript", "description": "Certified academic record"}
  ],
  "callback_url": "https://<public-host>/api/fastn/drive-sync"
}
```

Fastn must associate its Google OAuth connection with this applicant, not an admin or institution-wide account. It should return only file metadata the applicant has authorized: `name`, `webViewLink` (or `link`), and an optional `description`.

## Callback

Fastn can return the file list immediately in a `files` response property or post it asynchronously to `callback_url`:

```http
POST /api/fastn/drive-sync
X-Admitly-Drive-Sync-Secret: <shared secret>
Content-Type: application/json
```

```json
{
  "applicant_id": "42",
  "files": [
    {
      "name": "Jane_Doe_Research_Proposal.pdf",
      "webViewLink": "https://drive.google.com/file/d/.../view",
      "description": "Research proposal for the fellowship"
    }
  ]
}
```

Admitly marks only a high-confidence, unambiguous filename/description match as Received. Ambiguous files remain unassigned for manual review. It never receives or stores an applicant’s Google OAuth token.
