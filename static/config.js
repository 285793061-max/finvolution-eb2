/**
 * 微信公众号配置
 *
 * 使用说明：
 * 1. 登录微信公众号后台获取 AppID 和 AppSecret
 * 2. 在公众号设置中配置网页授权域名
 * 3. 建议通过后端环境变量配置：
 *    WECHAT_APP_ID / WECHAT_APP_SECRET
 * 4. 如只做本地演示，保持 enabled: false
 */
const WECHAT_CONFIG = {
    // 【必填】公众号AppID
    appId: '',

    // 不要把 AppSecret 放在前端文件中，请使用后端环境变量 WECHAT_APP_SECRET
    appSecret: '',

    // 【必填】授权回调域名（网页授权域名，如：example.com）
    redirectDomain: '',

    // 是否启用微信OAuth登录
    // false - 不启用（使用本地session）
    // true - 启用（需要配置以上三项）
    enabled: false
};

/**
 * 如果需要后端代理微信API（解决跨域问题），设置后端API地址
 * 不填写则直接请求微信API
 */
// const WECHAT_API_PROXY = '/api/wechat/auth';  // 后端代理接口
const WECHAT_API_PROXY = '';
