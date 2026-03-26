import ResultDataType from './result-data-model.mjs'
import { DefaultNode, BrowseNameDataType, DisplayNameDataType } from './default-node.mjs'
import { LocalizationModel, keyValuePair } from './support-models.mjs'
import ProcessingTimesDataType from './processing-times-data-type.mjs'
import TagDataType from './tag-data-type.mjs'
import TighteningResultDataType from './tightening-result-data-type.mjs'
import ResultValueDataType from './result-value-data-type.mjs'
import StepResultDataType from './step-result-data-type.mjs'
import ErrorInformationDataType from './error-information-data-type.mjs'
import { TighteningTraceDataType, StepTraceDataType, TraceContentDataType, TraceValueDataType } from './tightening-trace-data-type.mjs'

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

function eventTypeIdOf (msg) {
  const value = msg?.EventType?.value
  if (typeof value === 'string') {
    return value
  }
  if (value && typeof value.toString === 'function') {
    return value.toString()
  }
  return ''
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
    const eventType = eventTypeIdOf(msg)
    let model
    switch (eventType) {
      case ('TighteningSystemType'):
        model = new DefaultNode(msg, this)
        break
      case ('ResultManagementType'):
        model = new DefaultNode(msg, this)
        break
      default:
        if (/^ns=\d+;i=1007$/.test(eventType) && msg?.Result?.value) {
          model = new ResultDataType(msg.Result.value, this)
        } else {
          model = new DefaultNode(msg, this)
        }
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
      case ('ns=1;i=2001'):
        model = new ResultDataType(node.value.value, this)
        break
      default:
        model = new DefaultNode(node, this)
    }
    node.model = model
    return model
  }
}
