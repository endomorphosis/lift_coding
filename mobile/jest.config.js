module.exports = {
  testEnvironment: 'node',
  transform: {
    '^.+\\.[jt]sx?$': 'babel-jest',
  },
  testPathIgnorePatterns: ['/node_modules/'],
};
