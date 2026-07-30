const state = {
  config: null,
  xml: '',
  sha256: '',
  bodyText: ''
};

export function setDocumentState(nextState) {
  Object.assign(state, nextState);
}

export function getDocumentState() {
  return {
    ...state
  };
}
