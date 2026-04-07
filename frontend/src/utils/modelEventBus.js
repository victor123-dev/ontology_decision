/**
 * 业务模型和关系的事件总线
 * 用于在不同页面间同步数据变更
 */
class ModelEventBus {
  constructor() {
    this.events = {};
  }

  /**
   * 订阅事件
   * @param {string} event - 事件名称
   * @param {Function} callback - 回调函数
   */
  on(event, callback) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
  }

  /**
   * 取消订阅事件
   * @param {string} event - 事件名称
   * @param {Function} callback - 回调函数
   */
  off(event, callback) {
    if (this.events[event]) {
      this.events[event] = this.events[event].filter(cb => cb !== callback);
    }
  }

  /**
   * 触发事件
   * @param {string} event - 事件名称
   * @param {any} data - 事件数据
   */
  emit(event, data) {
    if (this.events[event]) {
      this.events[event].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Event ${event} handler error:`, error);
        }
      });
    }
  }

  // =============== 模型相关事件 ===============

  /**
   * 触发模型创建事件
   * @param {Object} model - 新创建的模型
   */
  emitModelCreated(model) {
    this.emit('model_created', { model });
  }

  /**
   * 触发模型更新事件
   * @param {string} modelId - 模型ID
   * @param {Object} updatedFields - 更新的字段
   */
  emitModelUpdated(modelId, updatedFields) {
    this.emit('model_updated', { modelId, updatedFields });
  }

  /**
   * 触发模型删除事件
   * @param {string} modelId - 被删除的模型ID
   */
  emitModelDeleted(modelId) {
    this.emit('model_deleted', { modelId });
  }

  // =============== 关系相关事件 ===============

  /**
   * 触发关系创建事件
   * @param {Object} link - 新创建的关系
   */
  emitLinkCreated(link) {
    this.emit('link_created', { link });
  }

  /**
   * 触发关系更新事件
   * @param {string} linkId - 关系ID
   * @param {Object} updatedFields - 更新的字段
   */
  emitLinkUpdated(linkId, updatedFields) {
    this.emit('link_updated', { linkId, updatedFields });
  }

  /**
   * 触发关系删除事件
   * @param {string} linkId - 被删除的关系ID
   */
  emitLinkDeleted(linkId) {
    this.emit('link_deleted', { linkId });
  }

  // =============== 行动相关事件 ===============

  /**
   * 触发行动创建事件
   * @param {Object} action - 新创建的行动
   */
  emitActionCreated(action) {
    this.emit('action_created', { action });
  }

  /**
   * 触发行动更新事件
   * @param {string} actionId - 行动ID
   * @param {Object} updatedFields - 更新的字段
   */
  emitActionUpdated(actionId, updatedFields) {
    this.emit('action_updated', { actionId, updatedFields });
  }

  /**
   * 触发行动删除事件
   * @param {string} actionId - 被删除的行动ID
   */
  emitActionDeleted(actionId) {
    this.emit('action_deleted', { actionId });
  }

  // =============== 字段相关事件 ===============

  /**
   * 触发字段创建事件
   * @param {string} modelId - 模型ID
   * @param {Object} field - 新创建的字段
   */
  emitFieldCreated(modelId, field) {
    this.emit('field_created', { modelId, field });
  }

  /**
   * 触发字段更新事件
   * @param {string} modelId - 模型ID
   * @param {string} fieldId - 字段ID
   * @param {Object} updatedFields - 更新的字段数据
   */
  emitFieldUpdated(modelId, fieldId, updatedFields) {
    this.emit('field_updated', { modelId, fieldId, updatedFields });
  }

  /**
   * 触发字段删除事件
   * @param {string} modelId - 模型ID
   * @param {string} fieldId - 被删除的字段ID
   */
  emitFieldDeleted(modelId, fieldId) {
    this.emit('field_deleted', { modelId, fieldId });
  }
}

// 创建单例实例
export const modelEventBus = new ModelEventBus();