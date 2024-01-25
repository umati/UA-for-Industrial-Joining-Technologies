import BaseEventModel from './BaseEventModel.mjs'

function cleanParameters (parameters) {
  const res = {}
  for (const [key, value] of Object.entries(parameters)) {
    if (!key.startsWith('Result')) {
      if (key.startsWith('JoiningSystemEventContent')) {
        const split = key.split('/')
        if (split.length > 1) {
          res[split.pop()] = value
        }
      } else {
        res[key] = value
      }
    }
  }
  return res
}

// The purpose of this class is to model the Event data structure
export default class JoiningSystemEventModel extends BaseEventModel {
  constructor (parameters, modelManager) {
    const castMapping = {
      AssociatedEntities: 'AssociatedEntities'
      // AssociatedEntities EventCode, EventText, Joiningtechnology ReportedValues
    }

    const parametersWithoutResult = cleanParameters(parameters)

    super(parametersWithoutResult, modelManager, castMapping)
  }
}
