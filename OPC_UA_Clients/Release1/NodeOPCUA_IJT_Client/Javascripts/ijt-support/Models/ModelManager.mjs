/* eslint-disable */
import ResultDataType from './ResultDataModel.mjs'
import { DefaultNode, BrowseNameDataType, DisplayNameDataType } from './DefaultNode.mjs'
import { LocalizationModel, keyValuePair } from './SupportModels.mjs'
import ProcessingTimesDataType from './ProcessingTimesDataType.mjs'
import TagDataType from './TagDataType.mjs'
import TighteningResultDataType from './TighteningResultDataType.mjs'
import ResultValueDataType from './ResultValueDataType.mjs'
import StepResultDataType from './StepResultDataType.mjs'
import ErrorInformationDataType from './ErrorInformationDataType.mjs'
import { TighteningTraceDataType, StepTraceDataType, TraceContentDataType, TraceValueDataType } from './TighteningTraceDataType.mjs'

const modelRegistry = {
  BrowseNameDataType,
  DisplayNameDataType,
  ErrorInformationDataType,
  LocalizationModel,
  ProcessingTimesDataType,
  ResultValueDataType,
  StepResultDataType,
  StepTraceDataType,
  TagDataType,
  TighteningResultDataType,
  TighteningTraceDataType,
  TraceContentDataType,
  TraceValueDataType,
  keyValuePair
}

export class ModelManager {
  /**
   * The purpose of this method is to create a javascript class from a parameter name
   * @param {*} parameterName
   * @param {*} content
   * @param {*} castMapping
   * @returns
   */
  factory (parameterName, content, castMapping) {
    if (typeof content === 'object' && !Array.isArray(content)) {
      if (content.dataType === 'ExtensionObject') {
        content = content.value
      }
      // If the model itself provides a typecasting, then use it
      if (castMapping) {
        for (const name of Object.entries(castMapping)) {
          if (parameterName.toLowerCase() === name[0].toLowerCase()) {
            const ctor = modelRegistry[name[1]]
            if (ctor) {
              return new ctor(content, this)
            }
            return content
          }
        }
      }
      // Else, handle simple types
      if (content && content.locale) {
        const a = {}
        a[parameterName] = content.text
        return new LocalizationModel(a, this)
      } else if (content && content.key) {
        const a = {}
        if (!content.value) {
          content.value = ''
        }
        a[content.key] = content.value
        return new LocalizationModel(a, this)
      }
      return content
    }
    return content
  }

  /**
   * This method handles the top level interpretation of a message that should be
   * converted to a model. 
   * @param {*} msg
   * @returns
   */
  createModelFromEvent (msg) {
    // console.log(node.nodeId)
    // console.log(node.typeName)
    let model
    switch (msg.EventType.value) {
      case ('TighteningSystemType'):
        model = new DefaultNode(msg, this)
        break
      case ('ResultManagementType'):
        model = new DefaultNode(msg, this)
        break
      case ('ns=4;i=1007'):
        model = new ResultDataType(msg.Result.value, this)
        break
      default:
        model = new DefaultNode(msg, this)
    }
    //node.model = model
    return model
  }
  /**
   * This method handles the top level interpretation of a message that should be
   * converted to a model. 
   * @param {*} values
   * @returns
   */
  createModelFromRead (values) {
    if (values.resultId) {
      return new ResultDataType(values, this)
    }
    return null
  }

  /**
   * This method handles the top level interpretation of a node that should be
   * converted to a model. This is probably unnecessary and could likely
   * be handled by the factory function with little modifications.
   * @param {*} node
   * @returns
   */
  createModelFromNode (node) {
    // console.log(node.nodeId)
    // console.log(node.typeName)
    let model
    switch (node.typeDefinition) {
      case ('TighteningSystemType'):
        model = new DefaultNode(node, this)
        break
      case ('ResultManagementType'):
        model = new DefaultNode(node, this)
        break
      case ('ns=4;i=2001'):
        model = new ResultDataType(node.value.value, this)
        break
      default:
        model = new DefaultNode(node, this)
    }
    node.model = model
    return model
  }

  /*
  // This method handles the top level interpretation of a message that should be
  // converted to a model. This is probably unnecessary and could likely
  // be handled by the factory function with little modifications.
  createModelFromMessage (path, dObject, cast) {
    let obj = {}
    if (!dObject.dataType) { // Unknown
      for (const [key, value] of Object.entries(dObject)) {
        console.log(`PARSING: ${key}: ${value}`)
        obj = value
      }
    } else if (dObject.dataType === 'ExtensionObject') { // Object
      if (dObject.arrayType === 'Scalar') {
        const key = path.split('/').pop()
        obj = this.factory(key, dObject.value, cast)
      } else if (dObject.arrayType === 'Array') { // Array
        console.log('PATH:' + path)
        const key = path.split('/').pop()
        const a = {}
        a[key] = dObject.value
        obj = this.factory(key, a, cast)
      }
    } else {
      const key = path.split('/').pop()
      const a = {
        key,
        value: dObject.value
      }
      obj = this.factory('keyValuePair', a, cast)
      return obj
    }
    return obj
  }*/
}
