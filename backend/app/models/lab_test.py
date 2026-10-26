"""
QuickDiagnosis - LabTest Domain Model (OOP Architecture)
Encapsulates individual laboratory test findings, numeric metrics,
immutable reference ranges (tuples), and deterministic status evaluation.
"""

from typing import Dict, Any, Optional, Tuple


class LabTest:
    """
    Represents an individual laboratory test metric.
    Demonstrates OOP encapsulation, data validation, and deterministic interpretation.
    """
    STATUS_LOW = "LOW"
    STATUS_NORMAL = "NORMAL"
    STATUS_HIGH = "HIGH"
    STATUS_UNKNOWN = "UNKNOWN"

    def __init__(
        self,
        test_name: str,
        value: float,
        unit: str = "",
        reference_low: Optional[float] = None,
        reference_high: Optional[float] = None,
        status: Optional[str] = None
    ):
        self._test_name: str = (test_name or "").strip()
        self._value: float = float(value)
        self._unit: str = (unit or "").strip()
        
        # Immutable reference range tuple: (low, high)
        self._reference_range: Tuple[Optional[float], Optional[float]] = (
            float(reference_low) if reference_low is not None else None,
            float(reference_high) if reference_high is not None else None
        )
        
        # Calculate status deterministically if not explicitly provided
        self._status: str = status if status else self.calculate_status()

    @property
    def test_name(self) -> str:
        return self._test_name

    @property
    def value(self) -> float:
        return self._value

    @property
    def unit(self) -> str:
        return self._unit

    @property
    def reference_low(self) -> Optional[float]:
        return self._reference_range[0]

    @property
    def reference_high(self) -> Optional[float]:
        return self._reference_range[1]

    @property
    def reference_range(self) -> Tuple[Optional[float], Optional[float]]:
        """Returns immutable reference range tuple."""
        return self._reference_range

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_abnormal(self) -> bool:
        """True if the test finding is abnormally LOW or HIGH."""
        return self._status in (self.STATUS_LOW, self.STATUS_HIGH)

    def calculate_status(self) -> str:
        """
        Interprets numeric value against reference range deterministically.
        Rules:
        - value < reference_low -> LOW
        - reference_low <= value <= reference_high -> NORMAL
        - value > reference_high -> HIGH
        - No valid range -> UNKNOWN
        """
        low, high = self._reference_range

        if low is None and high is None:
            return self.STATUS_UNKNOWN

        # If both bounds exist
        if low is not None and high is not None:
            if low > high:
                return self.STATUS_UNKNOWN
            if self._value < low:
                return self.STATUS_LOW
            elif self._value > high:
                return self.STATUS_HIGH
            else:
                return self.STATUS_NORMAL

        # If only upper bound exists (e.g. max limit)
        if high is not None:
            return self.STATUS_HIGH if self._value > high else self.STATUS_NORMAL

        # If only lower bound exists (e.g. minimum protective limit)
        if low is not None:
            return self.STATUS_LOW if self._value < low else self.STATUS_NORMAL

        return self.STATUS_UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        """Serializes object to a clean structured dictionary."""
        return {
            "test_name": self._test_name,
            "value": self._value,
            "unit": self._unit,
            "reference_low": self.reference_low,
            "reference_high": self.reference_high,
            "status": self._status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LabTest":
        """Instantiates LabTest from dictionary with type safety and error validation."""
        if not isinstance(data, dict):
            raise ValueError(f"Invalid lab test data structure: expected dict, got {type(data).__name__}")
        
        name = data.get("test_name") or data.get("name") or data.get("test")
        if not name or not str(name).strip():
            raise ValueError("Lab test name is required and cannot be empty")

        raw_val = data.get("value")
        if raw_val is None or str(raw_val).strip() == "":
            raise ValueError(f"Numeric value for test '{name}' is required")

        try:
            val_float = float(raw_val)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid non-numeric value '{raw_val}' for test '{name}'")

        ref_low = data.get("reference_low") or data.get("low") or data.get("min")
        ref_high = data.get("reference_high") or data.get("high") or data.get("max")

        low_val = None
        high_val = None
        if ref_low is not None and str(ref_low).strip() != "":
            try:
                low_val = float(ref_low)
            except (ValueError, TypeError):
                low_val = None

        if ref_high is not None and str(ref_high).strip() != "":
            try:
                high_val = float(ref_high)
            except (ValueError, TypeError):
                high_val = None

        unit = str(data.get("unit") or "").strip()
        status = data.get("status")

        return cls(
            test_name=str(name).strip(),
            value=val_float,
            unit=unit,
            reference_low=low_val,
            reference_high=high_val,
            status=status
        )

    def __repr__(self) -> str:
        return f"<LabTest {self._test_name}: {self._value} {self._unit} [{self._status}]>"
