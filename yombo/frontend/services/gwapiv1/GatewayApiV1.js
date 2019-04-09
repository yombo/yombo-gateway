import gwapiv1 from '@/services/gwapiv1'

export default {
    Devices () {
        return gwapiv1().get('devices')
    },
    Commands () {
        return gwapiv1().get('devices')
    },
    SystemInfo () {
        return gwapiv1().get('system/info', {withCredentials: true})
    },
}
