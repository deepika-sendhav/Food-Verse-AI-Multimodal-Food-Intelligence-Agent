# Food image recognition

The endpoint accepts a JPG, PNG, or WEBP file as multipart form data:

- **Method:** `POST`
- **Path:** `/api/food-recognition/analyze`
- **Upload field:** `file`
- **Swagger UI:** open `/docs`, expand `POST /api/food-recognition/analyze`, choose an image, and select **Execute**.

Successful responses contain `success`, `dish_name` (or `null` when unclear),
`detected_items`, `confidence` (`null` because the vision chat model does not
provide a calibrated classification probability), `description`, and
`uncertainties`. The vision model's dish and description are estimates, not
guaranteed identifications.

Configure the variables shown in the repository's `.env.example`. Run commands
from the repository root:

```powershell
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
python -m pytest backend/tests -q
```
