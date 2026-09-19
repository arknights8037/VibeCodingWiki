import { ElMessageBox } from 'element-plus';

export async function confirmRemoval(name: string, impact: string): Promise<boolean> {
  try {
    await ElMessageBox.confirm(`确定移除「${name}」？${impact}此操作无法撤销。`, '移除确认', {
      type: 'warning', confirmButtonText: '确认移除', cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger', autofocus: false,
    });
    return true;
  } catch { return false; }
}
