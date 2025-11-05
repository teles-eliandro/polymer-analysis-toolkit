from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
import pandas as pd
import io
from app.api.v1.schemas import MolecularInput, MolecularResult
from app.core.calculations import validate_inputs, calculate_molecular_properties

router = APIRouter(prefix="/molecular", tags=["Molecular Analysis"])

@router.post("/calc", response_model=MolecularResult)
async def calculate_molecular_properties_endpoint(
    data: MolecularInput = None,
    file: UploadFile = File(None)
):
    """
    Calculate Mn, Mw, and dispersity (Đ) from molecular masses and weight fractions.
    Provide either JSON `data` OR upload a CSV `file` with columns: 'massa', 'fracao'.
    """
    masses = []
    weight_fractions = []

    if data is None and file is None:
        raise HTTPException(status_code=400, detail="Provide either JSON data or a CSV file.")

    if data is not None and file is not None:
        raise HTTPException(status_code=400, detail="Provide either JSON data OR a CSV file, not both.")

    if data is not None:
        masses = data.masses
        weight_fractions = data.weight_fractions
    else:
        # Process CSV
        if file.content_type not in ["text/csv", "application/vnd.ms-excel"]:
            raise HTTPException(status_code=400, detail="File must be a CSV.")
        try:
            content = await file.read()
            df = pd.read_csv(io.StringIO(content.decode("utf-8")))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")

        required_columns = {"massa", "fracao"}
        if not required_columns.issubset(df.columns):
            raise HTTPException(
                status_code=400,
                detail=f"CSV must contain columns: {required_columns}. Found: {list(df.columns)}"
            )
        masses = df["massa"].tolist()
        weight_fractions = df["fracao"].tolist()

    # Validate and calculate
    try:
        validate_inputs(masses, weight_fractions)
        Mn, Mw, dispersity = calculate_molecular_properties(masses, weight_fractions)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

    return MolecularResult(Mn=Mn, Mw=Mw, dispersity=dispersity)