export function makeResultBundle (resultId) {
  return {
    type: 'ijt-result-export',
    version: 1,
    exportedAt: new Date().toISOString(),
    source: { app: 'compatibility-smoke', format: 'result-bundle' },
    results: [{
      ResultMetaData: {
        ResultId: resultId,
        Classification: '1',
        IsPartial: 'False',
        CreationTime: new Date().toISOString(),
      },
      ResultContent: [],
    }],
  }
}
