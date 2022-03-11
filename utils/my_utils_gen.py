import mmcv
import os.path as osp
from mmcv import Config
from mmgen.apis import train_model, init_model, sample_img2img_model
from mmgen.models import build_model
from mmgen.datasets import build_dataset
from mmcv.runner import load_checkpoint
from torchvision import utils
import time
import os


class MMGeneration:
    def __init__(self, 
        backbone='Pix2Pix',
        dataset_path = None
        ):

        self.config = './utils/models/Pix2Pix/Pix2Pix.py'
        self.checkpoint = './utils/models/Pix2Pix/pix2pix_edges2shoes.pth'

        self.backbone = backbone
        backbone_path = os.path.join('./utils/models', self.backbone)
        ckpt_cfg_list = list(os.listdir(backbone_path))
        for item in ckpt_cfg_list:
            if item[-1] == 'y':
                self.config = os.path.join(backbone_path, item)
            elif item[-1] == 'h':
                self.checkpoint = os.path.join(backbone_path, item)
            else:
                print("Warning!!! There is an unrecognized file in the backbone folder.")

        self.cfg = Config.fromfile(self.config)

        self.dataset_path = dataset_path
        self.lr = None
        self.backbonedict = {
            "Pix2Pix": './utils/models/Pix2Pix/Pix2Pix.py',
            # 下略
        }

        return None


    def train(self, random_seed=0, checkpoint = None, save_fold='./checkpoints', distributed=False, validate=True,
              total_iters=100, lr_generators = 0.002, lr_discriminators=0.002, weight_decay=0.001):
        # 加载网络模型的配置文件
        self.cfg = Config.fromfile(self.backbonedict[self.backbone])

        self.load_dataset(self.dataset_path)

        print("进行了cfg的切换")
        # 进行
        self.cfg.work_dir = self.save_fold
        # 创建工作目录
        mmcv.mkdir_or_exist(osp.abspath(self.cfg.work_dir))
        # 创建分类器
        datasets = [build_dataset(self.cfg.data.train)]
        model = build_model(self.cfg.model, train_cfg=self.cfg.train_cfg, test_cfg=self.cfg.test_cfg)
        if not checkpoint:
            model.init_weights()
        else:
            load_checkpoint(model, checkpoint)

        # 根据输入参数更新config文件
        self.cfg.total_iters = total_iters  # 学习率
        # self.cfg.optimizer.type = optimizer  # 优化器
        # self.cfg.optimizer.weight_decay = weight_decay  # 优化器的衰减权重
        # self.cfg.evaluation.metric = metric  # 验证指标
        # self.cfg.runner.max_epochs = epochs  # 最大的训练轮次

        # 设置每 5 个训练批次输出一次日志
        # self.cfg.log_config.interval = 1
        self.cfg.gpu_ids = range(1)

        self.cfg.seed = random_seed

        meta = dict()

        train_model(
            model,
            datasets,
            self.cfg,
            distributed=distributed,
            validate=validate,
            timestamp=time.strftime('%Y%m%d_%H%M%S', time.localtime()),
            meta=dict()
        )


    def inference(self,
                is_trained=False,
                pretrain_model="checkpoints/gen/ckpt/gen/latest.pth",
                infer_data="data/edges2shoes/val/1_AB.jpg",
                save_path = "result.png"):

        print("========= begin inference ==========")
        self.save_path = save_path

        checkpoint = self.checkpoint
        if is_trained:
            # 加载数据集及配置文件的路径
            checkpoint = pretrain_model
            self.load_dataset(self.dataset_path)
        model = init_model(self.cfg, checkpoint, device="cpu")
        result = sample_img2img_model(model, infer_data, self.cfg.target_domain) # 此处的model和外面的无关,纯局部变量
        result = (result[:, [2, 1, 0]] + 1.) / 2.
        # save images
        mmcv.mkdir_or_exist(os.path.dirname(self.save_path))
        utils.save_image(result, self.save_path)

    def load_dataset(self, path):
        self.dataset_path = path
        self.cfg.data.train.dataroot = self.dataset_path
        self.cfg.data.val.dataroot = self.dataset_path
        self.cfg.data.test.dataroot = self.dataset_path

        # self.cfg.data.train.dataroot = 'train'