const deleteAccountForm = document.getElementById('delete-account-form');

deleteAccountForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    try {
        const res = await fetch('/mypage/delete_account', {
            method: 'POST'
        });

        const result = await res.json();

        if (result.success) {
            alert(result.message);
            window.location.href = '/auth/login';  // 또는 '/' 홈 이동
        } else {
            alert(result.message);
        }
    } catch (err) {
        console.error('회원탈퇴 오류:', err);
        alert('서버 오류가 발생했습니다. 다시 시도해주세요.');
    }
});
