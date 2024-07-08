/**
 * The purpose of this class is encapsulating EntityDataType
 * https://reference.opcfoundation.org/IJT/Base/v100/docs/10.10#Table211
 *
 */
export class EntityDataType {
  constructor (name, description, entityId, entityOriginId, isExternal, entityType) {
    this.name = name
    this.description = description
    this.entityId = entityId
    this.entityOriginId = entityOriginId
    this.isExternal = isExternal
    this.entityType = entityType
  }
}

export const EntityTypes = {
  0: 'undefined',
  1: 'other',
  2: 'asset',
  3: 'controller',
  4: 'tool',
  5: 'servo',
  6: 'memory_device',
  7: 'sensor',
  8: 'cable',
  9: 'battery',
  10: 'power_supply',
  11: 'feeder',
  12: 'accessory',
  13: 'sub_component',
  14: 'software',
  15: 'result',
  16: 'event',
  17: 'error',
  18: 'system',
  19: 'log',
  20: 'vehicle',
  21: 'product',
  22: 'part',
  23: 'joint',
  24: 'model',
  25: 'order',
  26: 'joining_process',
  27: 'program',
  28: 'job',
  29: 'batch',
  30: 'recipe',
  31: 'task',
  32: 'process',
  33: 'configuration',
  34: 'socket',
  35: 'channel',
  36: 'station',
  37: 'production_line',
  38: 'location',
  39: 'user',
  40: 'parent',
  41: 'virtual_station'
}
