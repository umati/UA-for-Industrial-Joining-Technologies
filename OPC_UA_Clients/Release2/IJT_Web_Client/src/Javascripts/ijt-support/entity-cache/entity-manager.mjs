import { EntityCacheBase } from '../entity-cache-base.mjs'

/**
 * EntityCache — stores and indexes OPC UA entity nodes by type.
 *
 * Entities are grouped by EntityType (numeric key) in a plain object cache.
 * All mutations notify subscribers with the full cache and the changed entity.
 *
 * Extends {@link EntityCacheBase} — all cache/subscriber logic lives there.
 */
export class EntityCache extends EntityCacheBase {}
