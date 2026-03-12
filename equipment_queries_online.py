# -*- coding: utf-8 -*-
from __future__ import print_function

import cx_Oracle

connection = cx_Oracle.connect("bduser", "bdpass", "bdserverS", encoding='UTF-8', nencoding='UTF-8')
listaEquiposOnline = []

ESTADOS_MAP = {
    "activa": "Active",
    "en desarrollo": "Under Development",
    "descontinuada": "Discontinued",
    "desarrollado": "Developed",
    # atajos opcionales:
    "act": "Active", "dev": "In Development", "desc": "Discontinued"
}

def Online(estado_opcion="activa"):
    ''' Funcion para consulta equipos Online'''
    global connection, listaEquiposOnline
    
    estado = ESTADOS_MAP.get(estado_opcion.strip().lower())
    if not estado:
        raise ValueError(f"Estado inválido: {estado_opcion}. Usa: activa | en desarrollo | descontinuada")
    
    cursor = connection.cursor()
    cursor.execute("""
select * 
        from (            
        SELECT    a.PRD_OFF
        , a.NAME     Producto
        , a.status
        , c.NAME     Categoria
        , eqri.Valor "Código Equipo RI"
        , mdl.Valor  Modelo
        
		, ds.Valor Dual_SIM
		, tech.Valor Tecnologia
		, MemSz.Valor Memory_Size
        , ext.Valor  "External ID"
		,clr.objeto_color

        ,p_marca.value as marca
        ,p_color.value as color
        ,o_clr.colores
        ,price_component.name NRC_Value
        , eqgroup.valor "Equipment_group"
        ,product_asociaciones.name as asociaciones_oferta_producto,
        case
          when product_asociaciones.attr_id is null then
             ''
          else
             'Si'
        end as bulk_tree

    FROM      prd_app_6800.R_PIM_PRD_OFF                  a
    LEFT JOIN prd_app_6800.R_PIM_PCHLD_OF_RLHP            b ON a.PRD_OFF = b.CHILD
    LEFT JOIN prd_app_6800.R_PIM_OFFR_CAT                 c ON b.PARENT = c.OFFR_CAT

    -- Marca
    LEFT JOIN (SELECT PARENT_ID
                    , DEF_LIST_VALUE_TEXT  Valor
            FROM   prd_app_6800.R_PIM_OFFR_CHR_INV
            WHERE
                    PROD_OFF_CHAR = 9142360213165211308) marca ON marca.PARENT_ID = a.PRD_OFF
    -- Código Equipo RI
    LEFT JOIN (SELECT PARENT_ID
                    , DEFAULT_VALUE_TEXT Valor
            FROM   prd_app_6800.R_PIM_OFFR_CHR_INV
            WHERE
                    PROD_OFF_CHAR = 9142360213165211312) eqri ON eqri.PARENT_ID = a.PRD_OFF

    -- Modelo
    LEFT JOIN (SELECT PARENT_ID
                    , DEFAULT_VALUE_TEXT Valor
            FROM   prd_app_6800.R_PIM_OFFR_CHR_INV
            WHERE
                    PROD_OFF_CHAR = 9142360213165211316) mdl ON mdl.PARENT_ID = a.PRD_OFF
    -- Equipment_group
    LEFT JOIN (SELECT PARENT_ID
                    , DEFAULT_VALUE_TEXT Valor
            FROM   prd_app_6800.R_PIM_OFFR_CHR_INV
            WHERE
                    PROD_OFF_CHAR = 9150637937051085137) eqgroup ON eqgroup.PARENT_ID = a.PRD_OFF                  

    -- Color
    LEFT JOIN (SELECT PARENT_ID
                    , CAST(DEF_LIST_VALUE_TEXT AS varchar2(19)) Valor
                    ,OFFR_CHR_INV objeto_color
            FROM   prd_app_6800.R_PIM_OFFR_CHR_INV
            WHERE
                    PROD_OFF_CHAR = 9142360213165211382) clr ON clr.PARENT_ID = a.PRD_OFF
    -- Dual SIM
    LEFT JOIN (SELECT PARENT_ID
                    , DEFAULT_VALUE_TEXT Valor
                    ,OFFR_CHR_INV ds
            FROM   prd_app_6800.R_PIM_OFFR_CHR_INV
            WHERE
                    PROD_OFF_CHAR = 9142360213165211392) ds ON ds.PARENT_ID = a.PRD_OFF
    -- tech
    LEFT JOIN (SELECT PARENT_ID
                    , DEFAULT_VALUE_TEXT Valor
                    ,OFFR_CHR_INV ds
            FROM   prd_app_6800.R_PIM_OFFR_CHR_INV
            WHERE
                    PROD_OFF_CHAR = 9142360213165211506) tech ON tech.PARENT_ID = a.PRD_OFF
    -- MemSz
    LEFT JOIN (SELECT PARENT_ID
                    , DEFAULT_VALUE_NUMB Valor
                    ,OFFR_CHR_INV ds
            FROM   prd_app_6800.R_PIM_OFFR_CHR_INV
            WHERE
                    PROD_OFF_CHAR = 9150706682751795699) MemSz ON MemSz.PARENT_ID = a.PRD_OFF

    -- External ID
    LEFT JOIN (SELECT PARENT_ID
                    , DEFAULT_VALUE_NUMB Valor
            FROM   prd_app_6800.R_PIM_OFFR_CHR_INV
            WHERE
                    PROD_OFF_CHAR = 9142837021465565072) ext ON ext.PARENT_ID = a.PRD_OFF
    --Marca
    left join prd_app_6800.nc_params p_marca
    on p_marca.object_id = marca.valor
    and p_marca.attr_id = 9132206984813896491 
    --color
    left join prd_app_6800.nc_params p_color
    on p_color.object_id = clr.valor
    and p_color.attr_id = 9132206984813896491 
    left join (
    select a.object_id,
DBMS_LOB.SUBSTR(
  RTRIM(
    XMLAGG(XMLELEMENT(e, p.value || ',') ORDER BY p.value)
      .EXTRACT('//text()').getClobVal(),
    ','
  ),
  4000, 1
) AS colores


        from prd_app_6800.nc_references a
        join prd_app_6800.nc_params p
    on a.reference = p.object_id
        where ---a.object_id = 9164801126953324854 AND
        p.attr_id = 9132206984813896491 -- color
        and a.attr_id = 9135682520313500662
        group by a.object_id
    ) o_clr
    on o_clr.object_id = clr.objeto_color
/* asociaciones producto-oferta AGREGADAS (mismos nombres y alias) */
LEFT JOIN (
  SELECT
      r.reference,
      /* name = lista de asociaciones con el flag al lado de cada una */
DBMS_LOB.SUBSTR(
  RTRIM(
    XMLAGG(
      XMLELEMENT(e,
        a.name || ' (' ||
        CASE WHEN p.attr_id IS NOT NULL THEN 'Si' ELSE 'None' END ||
        ')' || ', '
      )
      ORDER BY a.name
    ).EXTRACT('//text()').getClobVal(),
    ', '
  ),
  4000, 1
) AS name

,  -- mismo nombre de columna
      /* attr_id = para mantener tu CASE general (bulk_tree) si lo seguís usando */
      MAX(p.attr_id) AS attr_id                   -- mismo nombre de columna
  FROM prd_app_6800.nc_objects a
  JOIN prd_app_6800.nc_references r ON a.object_id = r.object_id
  LEFT JOIN prd_app_6800.nc_params p
         ON p.object_id = r.object_id
        AND p.attr_id   = 9141020761413253837
  WHERE r.attr_id = 9125718672413237378
  GROUP BY r.reference
) product_asociaciones
  ON product_asociaciones.reference = a.prd_off

/* price component AGREGADO: mismo alias, NUEVA columna 'name' con los nombres */
LEFT JOIN (
  SELECT parent_id,
DBMS_LOB.SUBSTR(
  RTRIM(
    XMLAGG(XMLELEMENT(e, name || ', ') ORDER BY name)
      .EXTRACT('//text()').getClobVal(),
    ', '
  ),
  4000, 1
) AS name


  FROM PRD_APP_6800.R_PIM_OF_PR_CMPN
  WHERE name IS NOT NULL
  GROUP BY parent_id
) price_component
  ON price_component.parent_id = a.prd_off

WHERE
        SUBSTR(a.NAME, -6) = 'Online' 
        AND (
           ( :estado = 'Under Development' AND (a.status LIKE '%Under Development%' OR a.status LIKE '%Developed%') )
          OR ( :estado != 'Under Development' AND a.status LIKE '%' || :estado )
           ) 

         order by a.PRD_OFF
        )x 
        """,estado=estado )
    for row in cursor:
        listaEquiposOnline.append(list(row))

    return listaEquiposOnline


if __name__ == '__main__':
    Online()            
