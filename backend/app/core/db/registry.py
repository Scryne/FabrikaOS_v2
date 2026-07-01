"""Model kayıt noktası: tüm model modüllerini import ederek metadata'yı doldurur.

Alembic ``env.py`` ve provizyonlama bu modülü import ederek ``public_metadata`` /
``tenant_metadata``'nın tüm tabloları içerdiğinden emin olur. Yeni bir model modülü
eklendiğinde buraya import satırı eklenir.
"""

from __future__ import annotations

# public (control-plane) modelleri
import app.control_plane.models  # noqa: F401

# tenant şeması modelleri
import app.core.audit  # noqa: F401
import app.core.olaylar  # noqa: F401
import app.kimlik.models  # noqa: F401
import app.modules.bakim.models  # noqa: F401
import app.modules.enerji.models  # noqa: F401
import app.modules.isemri.models  # noqa: F401
import app.modules.kalite.models  # noqa: F401
import app.modules.saha.models  # noqa: F401
import app.modules.stok.models  # noqa: F401
import app.modules.uretim.models  # noqa: F401
from app.core.db.base import PublicBase, TenantBase

public_metadata = PublicBase.metadata
tenant_metadata = TenantBase.metadata
