import IJTBaseModel from '../IJTBaseModel.mjs'

// The purpose of this class is to model the Event data structure
export default class BaseEventType extends IJTBaseModel {
  getEventName () {
    if (this.ConditionClassName) {
      let evtName = this.ConditionClassName.Text + ' [ '
      for (const subclass of this.ConditionSubClassName) {
        evtName += subclass.Text + ' '
      }
      return evtName + ']'
    } else if (this.Result) {
      return 'ResultEvent'
    }
  }
}
