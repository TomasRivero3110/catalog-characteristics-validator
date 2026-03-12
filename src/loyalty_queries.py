# -*- coding: utf-8 -*-
import cx_Oracle

# Conexión
connection = cx_Oracle.connect(
    "bduser", "bdpass", "bdserverS",
    encoding='UTF-8', nencoding='UTF-8'
)

# Mapear los estados a como están en la DB
ESTADOS_MAP = {
    "activa": "Active",
    "en desarrollo": "Under Development",
    "descontinuada": "Discontinued",
    # atajos
    "act": "Active",
    "dev": "Under Development",
    "desc": "Discontinued"
}

def Loyalty(estado_opcion="activa"):
    """Consulta de equipos (loyalty) -> 1 fila por offering."""
    estado = ESTADOS_MAP.get(str(estado_opcion).strip().lower())
    if not estado:
        raise ValueError(
            f"Estado inválido: {estado_opcion}. Usa: activa | en desarrollo | descontinuada"
        )

    listaLoyalty = []
    cur = connection.cursor()

    # 1) Ejecutar ALTER SESSION por separado
    cur.execute("ALTER SESSION SET CURRENT_SCHEMA = PRD_APP_6800")

    # 2) Consulta ya agrupada
    sql = """
WITH po_loi AS (
  SELECT po.object_id           AS po_oi,
         po.name                AS po_name,
         loi.object_id          AS loi_oi,
         po_stat_val.value      AS po_stat,
         loi_red_rate.value     AS loi_red_rate
  FROM nc_references loi_ref
  JOIN nc_objects   loi          ON (loi_ref.object_id = loi.object_id)
  JOIN nc_objects   po           ON (loi_ref.reference = po.object_id)
  JOIN nc_params    po_stat      ON (po.object_id = po_stat.object_id)
  JOIN nc_params    loi_red_rate ON (loi.object_id = loi_red_rate.object_id)
  JOIN nc_list_values po_stat_val ON (po_stat.list_value_id = po_stat_val.list_value_id)
  WHERE loi_ref.attr_id = 9140823141613335528     /* Offering */
    AND loi_ref.reference IN (
      SELECT ch.reference
      FROM  nc_references par
      JOIN  nc_references ch ON (par.object_id = ch.object_id)
      WHERE par.attr_id = 9135377944913415569     /* Parent */
        AND par.reference = 9142360187965786685   /* Celulares */
        AND ch.attr_id = 9135378710613415627      /* Child */
    )
    AND po_stat.attr_id       = 7021759771013444983
    AND loi_red_rate.attr_id  = 9141135000313293172
    AND po_stat_val.value     = :estado
),
loi_lp AS (
  SELECT CONNECT_BY_ROOT object_id AS loi_oi,
         t.object_id               AS lp_oi,
         t.name                    AS lp_name
  FROM nc_objects t
  WHERE t.object_type_id = 9140476559813236079
  START WITH object_id IN (SELECT loi_oi FROM po_loi)
  CONNECT BY object_id = PRIOR parent_id
),
base AS (
  SELECT DISTINCT
         p.po_oi,
         p.po_name,
         p.po_stat,
         l.lp_name,
         TO_CHAR(p.loi_red_rate, 'FM9999990D999999', 'NLS_NUMERIC_CHARACTERS=.,') AS rate_s,
         l.lp_name || ':' ||
         TO_CHAR(p.loi_red_rate, 'FM9999990D999999', 'NLS_NUMERIC_CHARACTERS=.,') AS pair_s
  FROM po_loi p
  JOIN loi_lp l ON (p.loi_oi = l.loi_oi)
)
SELECT
  b.po_oi    AS "Offering ID",
  b.po_name  AS "Offering Name",
  b.po_stat  AS "Offering Status",
  LISTAGG(b.lp_name, '; ') WITHIN GROUP (ORDER BY b.lp_name)  AS "Loyalty Programs",
  LISTAGG(b.rate_s,  '; ') WITHIN GROUP (ORDER BY b.rate_s)   AS "One Time Redemption Rates",
  LISTAGG(b.pair_s,  '; ') WITHIN GROUP (ORDER BY b.lp_name)  AS "Program:Rate Map"
FROM base b
GROUP BY b.po_oi, b.po_name, b.po_stat
ORDER BY b.po_oi DESC
"""

    cur.execute(sql, estado=estado)
    for row in cur:
        listaLoyalty.append(list(row))

    cur.close()
    return listaLoyalty

if __name__ == '__main__':
    # prueba rápida
    for r in Loyalty("activa")[:5]:
        print(r)
