import ResultValueDataType from './results/result-value-data-type.mjs'
import { DefaultNode, BrowseNameDataType, DisplayNameDataType } from './default-node.mjs'
import TighteningDataType from './results/tightening-data-type.mjs'
import BatchDataModel from './results/batch-data-type.mjs'
import JobDataModel from './results/job-data-model.mjs'
import ResultDataType from './results/result-data-type.mjs'
import JoiningResultDataType from './results/joining-result-data-type.mjs'
import StepResultDataType from './results/step-result-data-type.mjs'
import TagDataType from './tag-data-type.mjs'
import {
  LocalizationModel,
  KeyValuePair,
  NodeId,
  ErrorInformationDataType,
  ProcessingTimesDataType
} from './support-models.mjs'
import { TighteningTraceDataType, StepTraceDataType, TraceContentDataType, TraceValueDataType } from './results/tightening-trace-data-type.mjs'
import ResultMetaData from './results/result-meta-data.mjs'
import ResultCounters from './results/result-counters.mjs'
import JoiningSystemEventModel from './events/joining-system-event-model.mjs'
import { EntityDataType } from './entities/entity-data-type.mjs'
import JoiningSystemResultReadyEvent from './events/joining-system-result-ready-event-model.mjs'
import IJTBaseModel from './ijt-base-model.mjs'

/** OPC UA IJT result classification IDs */
const RESULT_CLASS = Object.freeze({
  TIGHTENING: 1,
  BATCH: 3,
  JOB: 4,
  OTHER: 0,
})

/** OPC UA IJT event type identifiers */
const EVENT_TYPE_ID = Object.freeze({
  RESULT_READY: 1006,
  RESULT_RESPONSE: 1007,
  JOINING_RESULT: 1002,
})

const MODEL_CONSTRUCTORS = {
  ResultValueDataType,
  BrowseNameDataType,
  DisplayNameDataType,
  TighteningDataType,
  BatchDataModel,
  JobDataModel,
  ResultDataType,
  JoiningResultDataType,
  StepResultDataType,
  TagDataType,
  LocalizationModel,
  KeyValuePair,
  NodeId,
  ErrorInformationDataType,
  ProcessingTimesDataType,
  TighteningTraceDataType,
  StepTraceDataType,
  TraceContentDataType,
  TraceValueDataType,
  ResultMetaData,
  ResultCounters,
  EntityDataType
}

/* eslint-disable */
export class ModelManager {
  constructor (entityManager, jointManager) {
    this.resultSubscribeList = []
    this.entityManager = entityManager
    this.jointManager = jointManager
  }

  resultTypeNotification(result) {
    for (const f of this.resultSubscribeList) {
      f(result)
    }
  }

  subscribeSubResults(f) {
    this.resultSubscribeList.push(f)
  }

  /**
   * The purpose of this method is to create a javascript class from a parameter name
   * @param {*} parameterName
   * @param {*} content
   * @param {*} castMapping
   * @returns
   */
  factory (parameterName, content, castMapping) {
    if (content !== null && typeof content === 'object' && !Array.isArray(content)) {

      // console.log('Factory parameterName: ' + parameterName)
      if (content.dataType === 'ExtensionObject') {
        content = content.value
      }
      // If the model itself provides a typecasting, then use it
      
      if ( castMapping) {
        for (const name of Object.entries(castMapping)) {
          if (parameterName.toLowerCase() === name[0].toLowerCase()) {
            // console.log('Parameter to be cast: ' + name[0].toLowerCase())
            const resultMetaData = content.ResultMetaData || content.Value?.ResultMetaData
            // const resultMetaData = content.ResultMetaData || content.Value?.ResultMetaData
            if (resultMetaData && resultMetaData.CreationTime) { // We got a result
                const classification = resultMetaData.Classification 
                let result
                
                // console.log('Classification number' + classification)
                switch (parseInt(classification)) {
                  case RESULT_CLASS.JOB: 
                    result= new JobDataModel(content, this)
                    break
                  case RESULT_CLASS.BATCH: 
                    result = new BatchDataModel(content, this)
                    break
                  case RESULT_CLASS.TIGHTENING: 
                    result = new TighteningDataType(content, this)
                    break
                  default:
                    result = new ResultDataType(content, this)
                 }
                 this.resultTypeNotification(result)
                 return result
            } else { // Some non-result data structure
              const Ctor = MODEL_CONSTRUCTORS[name[1]]
              if (Ctor) {
                return new Ctor(content, this)
              }
              return new IJTBaseModel(content, this, castMapping)
            }
          }
        }
      }
      // Else, handle simple types
      if (content && content.Locale) {
        return new LocalizationModel(content, this)
      } else if (content && (
          content.pythonclass === 'NodeId' || 
          content.pythonclass === 'QualifiedName')) {
        return new NodeId(content, this)
      } else if (content && content.key) {
        const a = {}
        if (!content.value) {
          content.value = ''
        }
        a[content.key] = content.value
        return new LocalizationModel(a, this)
      } else {
        // console.log('Factory: '+parameterName)
        return new IJTBaseModel(content, this, castMapping)
      }

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
    let model
    switch (parseInt(msg.EventType.Identifier)) {
      case (EVENT_TYPE_ID.RESULT_READY):
        model = new JoiningSystemEventModel(msg, this)
        break
      case (EVENT_TYPE_ID.RESULT_RESPONSE):
        model = new JoiningSystemResultReadyEvent(msg, this)
        break
      case (EVENT_TYPE_ID.JOINING_RESULT): // Some non tightening related result
        model = new JoiningSystemResultReadyEvent(msg, this)
        break
      default:
        model = new DefaultNode(msg, this)
    }
    return model
  }
  /**
   * This method handles the top level interpretation of a message that should be
   * converted to a model. 
   * @param {*} values
   * @returns
   */
  createModelFromRead (values) {
    if (values.ResultMetaData) {
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
}
