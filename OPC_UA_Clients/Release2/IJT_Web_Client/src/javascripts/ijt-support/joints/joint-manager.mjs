import { EntityCacheBase } from '../entity-cache-base.mjs'

/**
 * JointManager — stores and indexes OPC UA joint entity nodes by type.
 *
 * Mirrors EntityCache but is scoped exclusively to joint-related entities,
 * keeping the joint view separate from the general entity cache.
 *
 * Extends {@link EntityCacheBase} — all cache/subscriber logic lives there.
 */
export class JointManager extends EntityCacheBase {}
