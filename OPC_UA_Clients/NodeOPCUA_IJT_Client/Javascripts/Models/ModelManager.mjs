/* eslint-disable */
import ResultValueDataType from './ResultValueDataType.mjs'
import ProcessingTimesDataType from './ProcessingTimesDataType.mjs'
import { DefaultNode, BrowseNameDataType, DisplayNameDataType } from './DefaultNode.mjs'
import ErrorInformationDataType from './ErrorInformationDataType.mjs'
import TighteningResultDataType from './TighteningResultDataType.mjs'
import ResultDataType from './ResultDataModel.mjs'
import StepResultDataType from './StepResultDataType.mjs'
import TagDataType from './TagDataType.mjs'
import { LocalizationModel, keyValuePair } from './SupportModels.mjs'
import { TighteningTraceDataType, StepTraceDataType, TraceContentDataType, TraceValueDataType } from './TighteningTraceDataType.mjs'
/* eslint-disable */
export default class ModelManager {
  /**
   * The purpose of this method is to create a javascript class from a parameter name
   * @param {*} parameterName
   * @param {*} content
   * @param {*} castMapping
   * @returns
   */
  factory (parameterName, content, castMapping) {
    if (typeof content === 'object' && Array !== content.constructor) {
      let obj
      if (content.dataType === 'ExtensionObject') {
        content = content.value
      }
      // If the model itself provides a typecasting, then use it
      if (castMapping) {
        for (const name of Object.entries(castMapping)) {
          if (parameterName.toLowerCase() === name[0].toLowerCase()) {
            return eval('new ' + name[1] + '(content,this)') // eslint-disable-line
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
      return obj
    }
    return content
  }

  /**
   * This method handles the top level interpretation of a message that should be
   * converted to a model. 
   * @param {*} msg
   * @returns
   */
  createModelFromMessage (msg) {
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
