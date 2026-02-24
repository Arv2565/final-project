export function getCookie(str) {
    const arr = document.cookie.split(';')
    const cookies = arr.map(cookie => {
        return { type: cookie.split('=')[0]?.trim(), val: cookie.split('=')[1]?.trim() }
    })
    const result = cookies.find(cookie => cookie.type == str)
    return result?.val
}
