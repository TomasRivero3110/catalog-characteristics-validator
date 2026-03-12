# -*- coding: utf-8 -*-
from __future__ import print_function

import cx_Oracle

connection = cx_Oracle.connect("bduser", "bdpass", "bdserverS", encoding='UTF-8', nencoding='UTF-8')
listaEquiposFP = []

ESTADOS_MAP = {
    "activa": "Active",
    "en desarrollo": "Under Development",
    "descontinuada": "Discontinued",
    # atajos opcionales:
    "act": "Active", "dev": "In Development", "desc": "Discontinued"
}

def EquiposFP(estado_opcion="activa"):
    ''' Funcion para consulta equipos Online'''
    global connection, listaEquiposFP
    estado = ESTADOS_MAP.get(estado_opcion.strip().lower())
    if not estado:
        raise ValueError(f"Estado inválido: {estado_opcion}. Usa: activa | en desarrollo | descontinuada")
    
    cursor = connection.cursor()
    cursor.execute("""
SELECT *
FROM (
    SELECT
       a.prd_off,
       a.name AS producto,
       a.status,       
       c.name AS categoria,
       c.offr_cat,
       eqri.valor AS "Código Equipo RI",
       mdl.valor  AS modelo,
       --clr.valor AS color,
       ext.valor  AS "External ID",
       p.value    AS color,
       o_clr.colores,
       product_asociaciones.name AS asociaciones_oferta_producto,
       CASE
         WHEN product_asociaciones.attr_id IS NULL THEN ''
         ELSE 'Si'
       END AS bulk_tree
    FROM prd_app_6800.r_pim_prd_off a
    LEFT JOIN prd_app_6800.r_pim_pchld_of_rlhp b
           ON a.prd_off = b.child
    LEFT JOIN prd_app_6800.r_pim_offr_cat c
           ON b.parent = c.offr_cat

    /* Código Equipo RI */
    LEFT JOIN (
      SELECT parent_id, default_value_text AS valor
      FROM   prd_app_6800.r_pim_offr_chr_inv
      WHERE  prod_off_char = 9142360213165211312
    ) eqri ON eqri.parent_id = a.prd_off

    /* Modelo */
    LEFT JOIN (
      SELECT parent_id, default_value_text AS valor
      FROM   prd_app_6800.r_pim_offr_chr_inv
      WHERE  prod_off_char = 9142360213165211316
    ) mdl ON mdl.parent_id = a.prd_off

    /* Color */
    LEFT JOIN (
      SELECT parent_id,
             CAST(def_list_value_text AS varchar2(19)) AS valor,
             offr_chr_inv AS objeto_color
      FROM   prd_app_6800.r_pim_offr_chr_inv
      WHERE  prod_off_char = 9142360213165211382
    ) clr ON clr.parent_id = a.prd_off

    /* External ID */
    LEFT JOIN (
      SELECT parent_id, default_value_numb AS valor
      FROM   prd_app_6800.r_pim_offr_chr_inv
      WHERE  prod_off_char = 9142837021465565072
    ) ext ON ext.parent_id = a.prd_off

    LEFT JOIN prd_app_6800.nc_params p
           ON p.object_id = clr.valor
          AND p.attr_id   = 9132206984813896491  -- color

    LEFT JOIN (
      SELECT a.object_id,
DBMS_LOB.SUBSTR(
  RTRIM(
    XMLAGG(XMLELEMENT(e, p.value || ',') ORDER BY p.value)
      .EXTRACT('//text()').getClobVal(),
    ','
  ),
  4000, 1
) AS colores



      FROM   prd_app_6800.nc_references a
      JOIN   prd_app_6800.nc_params p ON a.reference = p.object_id
      WHERE  p.attr_id = 9132206984813896491     -- color
        AND  a.attr_id = 9135682520313500662
      GROUP BY a.object_id
    ) o_clr ON o_clr.object_id = clr.objeto_color

    /* asociaciones producto-oferta (tal cual tus nombres/alias) */
    LEFT JOIN (
      SELECT a.name,
             r.reference,
             p.attr_id
      FROM   prd_app_6800.nc_objects a
      JOIN   prd_app_6800.nc_references r ON a.object_id = r.object_id
      LEFT JOIN prd_app_6800.nc_params p
             ON p.object_id = r.object_id
            AND p.attr_id   = 9141020761413253837
      WHERE  r.attr_id = 9125718672413237378
    ) product_asociaciones
      ON product_asociaciones.reference = a.prd_off

    /* Unificás acá las categorías que antes estabas consultando en un 2º SELECT */
    WHERE
         (
           ( :estado = 'Under Development' AND (a.status LIKE '%Under Development%' OR a.status LIKE '%Developed%') )
          OR ( :estado != 'Under Development' AND a.status LIKE '%' || :estado )
         ) 
         and c.OFFR_CAT =9142645245865649158
         order by a.prd_off

          ) x
          """, estado=estado)
    for row in cursor:
        listaEquiposFP.append(list(row))

    return listaEquiposFP


if __name__ == '__main__':
    EquiposFP()            
