import IJTBaseModel from './ijt-base-model.mjs'

// The purpose of this class is to model the Processing times data structure
export class DefaultNode extends IJTBaseModel {
  constructor (node, modelManager) {
    const castMapping = {
      browseName: 'BrowseNameDataType',
      displayName: 'DisplayNameDataType'
    }
    // node may be a browse node (has .browseData) or a raw event message
    const parameters = node?.browseData ?? node ?? {}
    super(parameters, modelManager, castMapping)
    if (node?.value) {
      this.value = node.value
    }
    this.relations = node?.relations
  }
}

// The purpose of this class is to
export class BrowseNameDataType extends IJTBaseModel {
}

// The purpose of this class is to
export class DisplayNameDataType extends IJTBaseModel {
}
