"""
shopify_writer.py — All Admin GraphQL write operations.
Called only by agent/tools.py. Never called directly from routes.

Every write function:
  1. Executes the Shopify Admin GraphQL mutation
  2. Saves a backup row in fix_backups (via db/queries.py)
  3. Returns the shopify_gid of the written resource (or script_tag_id)
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

from app.db.queries import (
    save_fix_backup,
    get_fix_backup,
    list_fix_backups_for_prefix,
    mark_fix_rolled_back,
)

logger = logging.getLogger(__name__)

_ADMIN_API_VERSION = "2024-01"


# ---------------------------------------------------------------------------
# Shared Admin GraphQL caller (same pattern as ingestion.py)
# ---------------------------------------------------------------------------

async def _admin_graphql(
    store_domain: str,
    token: str,
    query: str,
    variables: Optional[dict] = None,
) -> dict:
    """Execute an Admin GraphQL mutation and return the response body dict.

    Raises RuntimeError on GraphQL errors or HTTP errors.
    """
    url = f"https://{store_domain}/admin/api/{_ADMIN_API_VERSION}/graphql.json"
    payload: dict = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        body = response.json()

    if "errors" in body:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body


# ---------------------------------------------------------------------------
# productUpdate — shared helper for title / product_type / taxonomy
# ---------------------------------------------------------------------------

_MUTATION_PRODUCT_UPDATE = """
mutation ProductUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id title productType }
    userErrors { field message }
  }
}
"""

_QUERY_PRODUCT_SNAPSHOT = """
query ProductSnapshot($id: ID!) {
  product(id: $id) {
    id
    title
    category {
      id
    }
    metafields(first: 50) {
      edges {
        node { namespace key value type }
      }
    }
  }
}
"""

_QUERY_FILE_ALT = """
query FileAlt($id: ID!) {
  node(id: $id) {
    ... on MediaImage {
      id
      image { altText }
    }
  }
}
"""

_QUERY_METAFIELD_DEFINITIONS = """
query MetafieldDefinitions {
  metafieldDefinitions(first: 100, ownerType: PRODUCT) {
    edges {
      node { namespace key }
    }
  }
}
"""


def _encode_metafield_backup(
    original_value: Optional[str],
    existed_before: bool,
    original_type: Optional[str],
) -> str:
    return json.dumps(
        {
            "kind": "metafield_backup",
            "existed_before": existed_before,
            "value": original_value,
            "type": original_type,
        }
    )


def _decode_metafield_backup(raw: Optional[str]) -> tuple[bool, Optional[str], Optional[str]]:
    if not raw:
        return False, None, None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return True, raw, None
    if isinstance(parsed, dict) and parsed.get("kind") == "metafield_backup":
        return (
            bool(parsed.get("existed_before")),
            parsed.get("value"),
            parsed.get("type"),
        )
    return True, raw, None


async def _get_product_metafield_snapshot(
    store_domain: str,
    token: str,
    product_gid: str,
) -> dict[tuple[str, str], tuple[Optional[str], Optional[str]]]:
    body = await _admin_graphql(store_domain, token, _QUERY_PRODUCT_SNAPSHOT, {"id": product_gid})
    edges = ((body.get("data", {}) or {}).get("product") or {}).get("metafields", {}).get("edges", [])
    return {
        (edge["node"].get("namespace"), edge["node"].get("key")): (
            edge["node"].get("value"),
            edge["node"].get("type"),
        )
        for edge in edges
    }


async def _product_update(store_domain: str, token: str, product_gid: str, fields: dict) -> str:
    """Call productUpdate with arbitrary fields. Returns the product GID."""
    variables = {"input": {"id": product_gid, **fields}}
    body = await _admin_graphql(store_domain, token, _MUTATION_PRODUCT_UPDATE, variables)
    errors = body.get("data", {}).get("productUpdate", {}).get("userErrors", [])
    if errors:
        raise RuntimeError(f"productUpdate userErrors: {errors}")
    return product_gid


# ---------------------------------------------------------------------------
# write_title
# ---------------------------------------------------------------------------

async def write_title(
    store_domain: str,
    token: str,
    product_gid: str,
    new_title: str,
    original_title: str,
    job_id: str,
    fix_id: str,
) -> str:
    product_id = product_gid.rsplit("/", 1)[-1]
    await save_fix_backup(
        job_id=job_id,
        fix_id=fix_id,
        product_id=product_id,
        field_type="title",
        field_key="title",
        original_value=original_title,
        new_value=new_title,
        shopify_gid=product_gid,
    )
    await _product_update(store_domain, token, product_gid, {"title": new_title})
    return product_gid


# ---------------------------------------------------------------------------
# write_product_type
# ---------------------------------------------------------------------------

async def write_product_type(
    store_domain: str,
    token: str,
    product_gid: str,
    new_product_type: str,
    original_product_type: str,
    job_id: str,
    fix_id: str,
) -> str:
    product_id = product_gid.rsplit("/", 1)[-1]
    await save_fix_backup(
        job_id=job_id,
        fix_id=fix_id,
        product_id=product_id,
        field_type="product_type",
        field_key="product_type",
        original_value=original_product_type,
        new_value=new_product_type,
        shopify_gid=product_gid,
    )
    await _product_update(store_domain, token, product_gid, {"productType": new_product_type})
    return product_gid


# ---------------------------------------------------------------------------
# write_taxonomy — productUpdate with category field (Standard Taxonomy GID)
# ---------------------------------------------------------------------------

async def write_taxonomy(
    store_domain: str,
    token: str,
    product_gid: str,
    taxonomy_gid: str,
    original_taxonomy_gid: Optional[str],
    job_id: str,
    fix_id: str,
) -> str:
    product_id = product_gid.rsplit("/", 1)[-1]
    await save_fix_backup(
        job_id=job_id,
        fix_id=fix_id,
        product_id=product_id,
        field_type="taxonomy",
        field_key="category",
        original_value=original_taxonomy_gid,
        new_value=taxonomy_gid,
        shopify_gid=product_gid,
    )
    # Shopify ProductInput expects `category: ID`, where the ID is a
    # `gid://shopify/TaxonomyCategory/...` value.
    mutation = """
    mutation SetTaxonomy($productId: ID!, $taxonomyNodeId: ID!) {
      productUpdate(input: {
        id: $productId,
        category: $taxonomyNodeId
      }) {
        product { id }
        userErrors { field message }
      }
    }
    """
    body = await _admin_graphql(store_domain, token, mutation, {
        "productId": product_gid,
        "taxonomyNodeId": taxonomy_gid,
    })
    errors = body.get("data", {}).get("productUpdate", {}).get("userErrors", [])
    if errors:
        raise RuntimeError(f"write_taxonomy userErrors: {errors}")
    return product_gid


# ---------------------------------------------------------------------------
# write_metafield — metafieldsSet
# ---------------------------------------------------------------------------

_MUTATION_METAFIELDS_SET = """
mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id key namespace value }
    userErrors { field message }
  }
}
"""


async def write_metafield(
    store_domain: str,
    token: str,
    product_gid: str,
    namespace: str,
    key: str,
    value: str,
    type_: str,
    job_id: str,
    fix_id: str,
) -> str:
    product_id = product_gid.rsplit("/", 1)[-1]
    existing_metafields = await _get_product_metafield_snapshot(store_domain, token, product_gid)
    current_value, current_type = existing_metafields.get((namespace, key), (None, None))
    existed_before = (namespace, key) in existing_metafields
    await save_fix_backup(
        job_id=job_id,
        fix_id=fix_id,
        product_id=product_id,
        field_type="metafield",
        field_key=f"{namespace}.{key}",
        original_value=_encode_metafield_backup(current_value, existed_before, current_type),
        new_value=value,
        shopify_gid=product_gid,
    )
    variables = {
        "metafields": [{
            "ownerId": product_gid,
            "namespace": namespace,
            "key": key,
            "value": value,
            "type": type_,
        }]
    }
    body = await _admin_graphql(store_domain, token, _MUTATION_METAFIELDS_SET, variables)
    errors = body.get("data", {}).get("metafieldsSet", {}).get("userErrors", [])
    if errors:
        raise RuntimeError(f"write_metafield userErrors: {errors}")
    return product_gid


# ---------------------------------------------------------------------------
# write_alt_text — fileUpdate for media image alt text
# ---------------------------------------------------------------------------

_MUTATION_FILE_UPDATE = """
mutation FileUpdate($files: [FileUpdateInput!]!) {
  fileUpdate(files: $files) {
    files { id alt }
    userErrors { field message }
  }
}
"""


async def write_alt_text(
    store_domain: str,
    token: str,
    image_gid: str,
    alt_text: str,
    original_alt: Optional[str],
    job_id: str,
    fix_id: str,
    product_id: Optional[str] = None,
) -> str:
    await save_fix_backup(
        job_id=job_id,
        fix_id=fix_id,
        product_id=product_id,
        field_type="image_alt",
        field_key="alt",
        original_value=original_alt,
        new_value=alt_text,
        shopify_gid=image_gid,
    )
    variables = {"files": [{"id": image_gid, "alt": alt_text}]}
    body = await _admin_graphql(store_domain, token, _MUTATION_FILE_UPDATE, variables)
    errors = body.get("data", {}).get("fileUpdate", {}).get("userErrors", [])
    if errors:
        raise RuntimeError(f"write_alt_text userErrors: {errors}")
    return image_gid


# ---------------------------------------------------------------------------
# inject_schema_script — scriptTagCreate
# ---------------------------------------------------------------------------

_MUTATION_SCRIPT_TAG_CREATE = """
mutation ScriptTagCreate($input: ScriptTagInput!) {
  scriptTagCreate(input: $input) {
    scriptTag { id src displayScope }
    userErrors { field message }
  }
}
"""


async def inject_schema_script(
    store_domain: str,
    token: str,
    schema_json: str,
    job_id: str,
    fix_id: str,
) -> str:
    """Inject JSON-LD schema via scriptTagCreate. Returns the script_tag_id GID.

    Shopify Script Tags load an external JS file URL — they cannot inline JSON-LD
    directly. We use a data URI workaround: encode the JSON-LD as a base64 data
    URI that creates and appends a <script type='application/ld+json'> element.

    In production, host the script at a CDN and pass the URL instead.
    """
    import base64

    js_payload = (
        "(function(){"
        "var s=document.createElement('script');"
        "s.type='application/ld+json';"
        f"s.textContent={repr(schema_json)};"
        "document.head.appendChild(s);"
        "})();"
    )
    encoded = base64.b64encode(js_payload.encode()).decode()
    script_src_url = f"data:text/javascript;base64,{encoded}"

    variables = {
        "input": {
            "src": script_src_url,
            "displayScope": "ONLINE_STORE",
        }
    }
    body = await _admin_graphql(store_domain, token, _MUTATION_SCRIPT_TAG_CREATE, variables)
    errors = body.get("data", {}).get("scriptTagCreate", {}).get("userErrors", [])
    if errors:
        raise RuntimeError(f"inject_schema_script userErrors: {errors}")

    script_tag_gid = body["data"]["scriptTagCreate"]["scriptTag"]["id"]

    await save_fix_backup(
        job_id=job_id,
        fix_id=fix_id,
        product_id=None,
        field_type="script_tag",
        field_key="scriptTagCreate",
        original_value=None,
        new_value=schema_json,
        shopify_gid=script_tag_gid,
        script_tag_id=script_tag_gid,
    )
    return script_tag_gid


# ---------------------------------------------------------------------------
# delete_schema_script — scriptTagDelete (rollback action)
# ---------------------------------------------------------------------------

_MUTATION_SCRIPT_TAG_DELETE = """
mutation ScriptTagDelete($id: ID!) {
  scriptTagDelete(id: $id) {
    deletedScriptTagId
    userErrors { field message }
  }
}
"""


async def delete_schema_script(store_domain: str, token: str, script_tag_gid: str) -> None:
    """Delete an injected script tag (used for rollback)."""
    body = await _admin_graphql(store_domain, token, _MUTATION_SCRIPT_TAG_DELETE, {"id": script_tag_gid})
    errors = body.get("data", {}).get("scriptTagDelete", {}).get("userErrors", [])
    if errors:
        raise RuntimeError(f"delete_schema_script userErrors: {errors}")


# ---------------------------------------------------------------------------
# create_metafield_definition — idempotent, no backup needed
# ---------------------------------------------------------------------------

_MUTATION_METAFIELD_DEF_CREATE = """
mutation MetafieldDefinitionCreate($definition: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $definition) {
    createdDefinition { id namespace key name }
    userErrors { field message code }
  }
}
"""


async def create_metafield_definition(
    store_domain: str,
    token: str,
    namespace: str,
    key: str,
    name: str,
    type_: str,
) -> Optional[str]:
    """Create a typed MetafieldDefinition for PRODUCT owner type.

    Idempotent — if a definition already exists with the same namespace+key,
    the TAKEN error is swallowed and None is returned.
    """
    variables = {
        "definition": {
            "name": name,
            "namespace": namespace,
            "key": key,
            "type": type_,
            "ownerType": "PRODUCT",
        }
    }
    body = await _admin_graphql(store_domain, token, _MUTATION_METAFIELD_DEF_CREATE, variables)
    errors = body.get("data", {}).get("metafieldDefinitionCreate", {}).get("userErrors", [])
    # TAKEN error means definition already exists — that's fine
    real_errors = [e for e in errors if e.get("code") != "TAKEN"]
    if real_errors:
        raise RuntimeError(f"create_metafield_definition userErrors: {real_errors}")

    created = body.get("data", {}).get("metafieldDefinitionCreate", {}).get("createdDefinition")
    return created["id"] if created else None


# ---------------------------------------------------------------------------
# rollback_fix — restore original value from fix_backups
# ---------------------------------------------------------------------------

async def rollback_fix(
    fix_id: str,
    store_domain: str,
    token: str,
    expected_job_id: str | None = None,
) -> tuple[str, str]:
    """Restore the original value for a fix. Returns (field, restored_value).

    Raises KeyError if fix_id not found. Raises RuntimeError on write failure.
    """
    backup = await get_fix_backup(fix_id)
    backups: list[dict] = []
    if backup is not None:
        backups = [backup]
    else:
        backups = await list_fix_backups_for_prefix(f"{fix_id}_")
    if expected_job_id is not None:
        backups = [row for row in backups if row.get("job_id") == expected_job_id]
    if not backups:
        raise KeyError(f"No backup found for fix_id={fix_id!r}")

    restored_fields: list[str] = []
    restored_values: list[str] = []
    for backup_row in reversed(backups):
        field, restored_value = await _rollback_single_backup(backup_row, store_domain, token)
        restored_fields.append(field)
        restored_values.append(restored_value)
        await mark_fix_rolled_back(backup_row["fix_id"])

    if len(restored_fields) == 1:
        return restored_fields[0], restored_values[0]
    return ("multiple_fields", f"Rolled back {len(restored_fields)} writes")


async def _rollback_single_backup(backup: dict, store_domain: str, token: str) -> tuple[str, str]:

    field_type = backup["field_type"]
    shopify_gid = backup["shopify_gid"]
    original_value = backup["original_value"]
    script_tag_id = backup.get("script_tag_id")
    restored_value = original_value or ""

    if field_type == "title":
        await _product_update(store_domain, token, shopify_gid, {"title": original_value or ""})

    elif field_type == "product_type":
        await _product_update(store_domain, token, shopify_gid, {"productType": original_value or ""})

    elif field_type == "taxonomy":
        if original_value:
            mutation = """
            mutation RestoreTaxonomy($productId: ID!, $taxonomyNodeId: ID!) {
              productUpdate(input: {
                id: $productId,
                productCategory: { productTaxonomyNodeId: $taxonomyNodeId }
              }) {
                product { id }
                userErrors { field message }
              }
            }
            """
            await _admin_graphql(store_domain, token, mutation, {
                "productId": shopify_gid,
                "taxonomyNodeId": original_value,
            })
        # If original was null, leave taxonomy as-is (cannot "unset" to null safely)

    elif field_type == "metafield":
        namespace, key = (backup.get("field_key") or ".").split(".", 1)
        existed_before, metafield_value, metafield_type = _decode_metafield_backup(original_value)
        restored_value = metafield_value or ""
        if existed_before:
            mutation = """
            mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
              metafieldsSet(metafields: $metafields) {
                metafields { id key namespace value }
                userErrors { field message }
              }
            }
            """
            await _admin_graphql(store_domain, token, mutation, {
                "metafields": [{
                    "ownerId": shopify_gid,
                    "namespace": namespace,
                    "key": key,
                    "value": metafield_value or "",
                    "type": metafield_type or "single_line_text_field",
                }]
            })
        else:
            mutation = """
            mutation MetafieldsDelete($metafields: [MetafieldIdentifierInput!]!) {
              metafieldsDelete(metafields: $metafields) {
                deletedMetafields { key namespace ownerId }
                userErrors { field message }
              }
            }
            """
            await _admin_graphql(store_domain, token, mutation, {
                "metafields": [{"ownerId": shopify_gid, "namespace": namespace, "key": key}]
            })

    elif field_type == "image_alt":
        await _admin_graphql(store_domain, token, _MUTATION_FILE_UPDATE, {
            "files": [{"id": shopify_gid, "alt": original_value or ""}]
        })

    elif field_type == "script_tag":
        if script_tag_id:
            await delete_schema_script(store_domain, token, script_tag_id)

    else:
        raise RuntimeError(f"Unknown field_type for rollback: {field_type!r}")
    return (backup.get("field_key") or field_type), restored_value


async def verify_fix_applied(
    store_domain: str,
    token: str,
    fix_id: str,
    fix_type: str,
) -> bool:
    """Verify a completed fix against live Shopify state when possible."""
    if fix_type == "create_metafield_definitions":
        body = await _admin_graphql(store_domain, token, _QUERY_METAFIELD_DEFINITIONS)
        defs = (body.get("data", {}).get("metafieldDefinitions", {}) or {}).get("edges", [])
        existing = {
            (edge["node"].get("namespace"), edge["node"].get("key"))
            for edge in defs
        }
        required = {
            ("custom", "material"),
            ("custom", "care_instructions"),
        }
        return required.issubset(existing)

    if fix_type == "fill_metafield":
        backups = await list_fix_backups_for_prefix(f"{fix_id}_")
        if not backups:
            return False
        product_gid = backups[0].get("shopify_gid")
        if not product_gid:
            return False
        live = {
            key: value
            for key, (value, _) in (await _get_product_metafield_snapshot(store_domain, token, product_gid)).items()
        }
        for backup in backups:
            field_key = backup.get("field_key") or ""
            if "." not in field_key:
                return False
            namespace, key = field_key.split(".", 1)
            if live.get((namespace, key)) != (backup.get("new_value") or ""):
                return False
        return True

    backup = await get_fix_backup(fix_id)

    if fix_type == "generate_alt_text":
        backups = await list_fix_backups_for_prefix(f"{fix_id}_")
        if not backups:
            backups = [backup] if backup is not None else []
        if not backups:
            return False
        for image_backup in backups:
            image_gid = image_backup.get("shopify_gid")
            if not image_gid:
                return False
            body = await _admin_graphql(store_domain, token, _QUERY_FILE_ALT, {"id": image_gid})
            node = (body.get("data", {}) or {}).get("node") or {}
            image = node.get("image") or {}
            if (image.get("altText") or "") != (image_backup.get("new_value") or ""):
                return False
        return True

    if backup is None:
        return False

    shopify_gid = backup.get("shopify_gid")
    expected = backup.get("new_value") or ""
    if not shopify_gid:
        return False

    if fix_type in {"improve_title", "map_taxonomy", "classify_product_type"}:
        body = await _admin_graphql(store_domain, token, _QUERY_PRODUCT_SNAPSHOT, {"id": shopify_gid})
        product = (body.get("data", {}) or {}).get("product") or {}
        if fix_type == "improve_title":
            return (product.get("title") or "") == expected
        if fix_type == "classify_product_type":
            return (product.get("productType") or "") == expected
        taxonomy = (product.get("category") or {}).get("id") or ""
        return taxonomy == expected

    return False


# ---------------------------------------------------------------------------
# validate_taxonomy_gid — confirm a GID refers to a real Shopify taxonomy node
# ---------------------------------------------------------------------------

_QUERY_TAXONOMY_NODE = """
query TaxonomyNode($id: ID!) {
  node(id: $id) {
    ... on TaxonomyCategory {
      id
      fullName
    }
  }
}
"""


async def validate_taxonomy_gid(
    store_domain: str,
    token: str,
    taxonomy_gid: str,
) -> bool:
    """Query Shopify Admin API to confirm the taxonomy GID exists.

    Returns False only when the API definitively says the node doesn't exist
    (null response). On any network/API error the function fails open — the
    calling tool should then let write_taxonomy's own userErrors catch bad IDs.
    """
    try:
        body = await _admin_graphql(store_domain, token, _QUERY_TAXONOMY_NODE, {"id": taxonomy_gid})
        node = (body.get("data", {}) or {}).get("node")
        return node is not None
    except Exception as exc:
        logger.warning(
            "validate_taxonomy_gid: could not verify %s against Shopify API, proceeding: %s",
            taxonomy_gid, exc,
        )
        return True  # fail open — let write_taxonomy's userErrors handle genuinely bad IDs
