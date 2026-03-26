/**
 * The purpose of this class is encapsulating EntityDataType
 * https://reference.opcfoundation.org/IJT/Base/v100/docs/10.10#Table211
 *
 */

import IJTBaseModel from '../ijt-base-model.mjs'

export class JointDataType extends IJTBaseModel {
  constructor (parameters, modelManager) {
    // constructor (name, description, entityId, entityOriginId, isExternal, entityType) {
    super(parameters, modelManager)

    if (modelManager && modelManager.jointManager) {
      modelManager.jointManager.addEntity(this)
    }
  }
}
