<?php
/**
 * 管理员登录页面
 * POST 提交用户名密码进行登录
 */

require_once __DIR__ . '/../includes/auth.php';
require_once __DIR__ . '/../includes/functions.php';

// 如果已登录，直接跳转后台首页
if (isset($_SESSION['admin_logged_in']) && $_SESSION['admin_logged_in'] === true) {
    header('Location: dashboard.php');
    exit;
}

$error = '';

// 处理登录表单提交
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = isset($_POST['username']) ? sanitizeInput($_POST['username']) : '';
    $password = isset($_POST['password']) ? $_POST['password'] : '';

    if (empty($username) || empty($password)) {
        $error = '请输入用户名和密码';
    } elseif (verifyAdmin($username, $password)) {
        setLoginSession($username);
        header('Location: dashboard.php');
        exit;
    } else {
        $error = '用户名或密码错误';
    }
}
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>管理员登录 — 宁波旅游后台</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #B8763E 0%, #3D7A5F 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }
        .login-card {
            background: #fff;
            border-radius: 16px;
            padding: 48px 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 16px 48px rgba(44, 24, 16, 0.2);
        }
        .login-card__brand {
            text-align: center;
            margin-bottom: 32px;
        }
        .login-card__icon {
            width: 56px;
            height: 56px;
            border-radius: 12px;
            object-fit: contain;
            margin-bottom: 12px;
        }
        .login-card__title {
            font-size: 22px;
            font-weight: 700;
            color: #2C1810;
        }
        .login-card__subtitle {
            font-size: 14px;
            color: #9E8C7E;
            margin-top: 4px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-label {
            display: block;
            font-size: 14px;
            font-weight: 600;
            color: #2C1810;
            margin-bottom: 8px;
        }
        .form-input {
            width: 100%;
            padding: 10px 16px;
            font-size: 15px;
            border: 2px solid #E8DDD1;
            border-radius: 8px;
            outline: none;
            transition: border-color 0.2s;
            font-family: inherit;
        }
        .form-input:focus {
            border-color: #B8763E;
            box-shadow: 0 0 0 3px rgba(184, 118, 62, 0.08);
        }
        .btn-login {
            width: 100%;
            padding: 12px;
            background: #B8763E;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            font-family: inherit;
        }
        .btn-login:hover {
            background: #8E5A2A;
        }
        .error-msg {
            background: #FEF2F2;
            color: #C4584A;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 14px;
            margin-bottom: 20px;
            border: 1px solid #FECACA;
        }
        .back-link {
            display: block;
            text-align: center;
            margin-top: 24px;
            font-size: 14px;
            color: #9E8C7E;
            text-decoration: none;
        }
        .back-link:hover { color: #B8763E; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="login-card__brand">
            <img src="../../images/favicon.ico" alt="宁波旅游" class="login-card__icon">
            <h1 class="login-card__title">后台管理系统</h1>
            <p class="login-card__subtitle">宁波旅游宣传网站</p>
        </div>

        <?php if ($error): ?>
            <div class="error-msg"><?php echo htmlspecialchars($error); ?></div>
        <?php endif; ?>

        <form method="POST" action="">
            <div class="form-group">
                <label class="form-label" for="username">用户名</label>
                <input type="text" class="form-input" id="username" name="username"
                       placeholder="请输入管理员用户名" required autofocus
                       value="<?php echo isset($username) ? htmlspecialchars($username) : ''; ?>">
            </div>
            <div class="form-group">
                <label class="form-label" for="password">密码</label>
                <input type="password" class="form-input" id="password" name="password"
                       placeholder="请输入密码" required>
            </div>
            <button type="submit" class="btn-login">登 录</button>
        </form>

        <a href="../index.html" class="back-link">← 返回网站首页</a>
    </div>
</body>
</html>
