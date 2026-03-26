import api from './api';

const nlRuleApi = {
  parseSensingConfig: (naturalLanguage) => {
    return api.post('/nl-rule-interface/parse-sensing-config', { natural_language: naturalLanguage });
  },
  
  parseDriveLogic: (naturalLanguage) => {
    return api.post('/nl-rule-interface/parse-drive-logic', { natural_language: naturalLanguage });
  },

};

export default nlRuleApi;