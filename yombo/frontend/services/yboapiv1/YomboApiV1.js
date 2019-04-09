import yboapiv1 from '@/services/yboapiv1'

export default {
    Devices () {
        return yboapiv1().get('devices')
    },
    Commands () {
        return yboapiv1().get('commands')
    },
}
