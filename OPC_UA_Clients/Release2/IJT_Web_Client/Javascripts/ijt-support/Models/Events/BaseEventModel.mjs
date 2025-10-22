import IJTBaseModel from '../IJTBaseModel.mjs'

// The purpose of this class is to model the Event data structure
export default class BaseEventType extends IJTBaseModel {
  getEventName () {
    if (this.ConditionClassName) {
      let evtName = this.ConditionClassName + ' [ '
      for (const subclass of this.ConditionSubClassName) {
        evtName += subclass + ' '
      }
      return evtName + ']'
    } else if (this.Result) {
      return 'ResultEvent'
    }
  }
}
